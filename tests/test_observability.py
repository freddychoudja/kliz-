"""Tests for logging, hooks and secret hygiene."""

import logging
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from conftest import FlakyProvider, StubProvider, make_mock_session, return_true

from kliz import (
    IndexNowProvider,
    Kliz,
    NotificationResult,
    ProviderError,
    RetryEvent,
    read_sitemap,
)
from kliz.cli import main

SECRET = "SuperSecretIndexNowKey123"


def test_library_installs_a_null_handler() -> None:
    handlers = logging.getLogger("kliz").handlers

    assert any(isinstance(h, logging.NullHandler) for h in handlers)


def test_on_result_receives_every_final_result() -> None:
    seen: list[NotificationResult] = []
    session = make_mock_session()
    session.post.return_value = Mock(status_code=200)
    indexer = Kliz(
        [IndexNowProvider(api_key=SECRET, session=session), StubProvider(return_true)],
        on_result=seen.append,
    )

    indexer.notify_many(["https://a.example/1", "https://a.example/2?x=1"])

    assert [(r.provider, r.success, r.urls) for r in seen] == [
        ("IndexNowProvider", False, ("https://a.example/2?x=1",)),
        ("IndexNowProvider", True, ("https://a.example/1",)),
        ("StubProvider", True, ("https://a.example/1",)),
        ("StubProvider", True, ("https://a.example/2?x=1",)),
    ]


def test_on_retry_receives_each_wait() -> None:
    events: list[RetryEvent] = []
    indexer = Kliz(
        [FlakyProvider(failures=2)],
        max_attempts=3,
        sleep=lambda _: None,
        on_retry=events.append,
    )

    assert indexer.notify_all("https://a.example/") == {"FlakyProvider": True}

    assert [(e.provider, e.attempt, e.urls) for e in events] == [
        ("FlakyProvider", 1, ("https://a.example/",)),
        ("FlakyProvider", 2, ("https://a.example/",)),
    ]
    assert all(isinstance(e.error, ProviderError) and e.delay > 0 for e in events)


def test_failing_hooks_are_logged_and_never_break_notifications(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def explode(_: object) -> None:
        raise RuntimeError("metrics backend down")

    indexer = Kliz(
        [FlakyProvider(failures=1)],
        max_attempts=2,
        sleep=lambda _: None,
        on_result=explode,
        on_retry=explode,
    )

    with caplog.at_level(logging.ERROR, logger="kliz"):
        assert indexer.notify_all("https://a.example/") == {"FlakyProvider": True}

    assert sum("hook" in r.getMessage() for r in caplog.records) == 2
    assert all(r.exc_info for r in caplog.records)


def test_outcomes_and_retries_are_logged(caplog: pytest.LogCaptureFixture) -> None:
    indexer = Kliz([FlakyProvider(failures=1)], max_attempts=2, sleep=lambda _: None)

    with caplog.at_level(logging.INFO, logger="kliz"):
        indexer.notify_all("https://a.example/")
        Kliz([StubProvider(lambda url: False)]).notify_many(
            ["https://a.example/1", "https://a.example/2"]
        )

    messages = [(r.levelname, r.getMessage()) for r in caplog.records]
    assert ("INFO", "FlakyProvider: notified 1 URL(s)") in messages
    assert any(
        level == "INFO" and "retrying in" in msg and "attempt 2 of 2" in msg
        for level, msg in messages
    )
    assert (
        "WARNING",
        "StubProvider: https://a.example/1 failed: provider returned False",
    ) in messages


def test_batch_failures_are_logged_with_their_size(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = make_mock_session()
    session.post.return_value = Mock(status_code=403, headers={})
    indexer = Kliz([IndexNowProvider(api_key=SECRET, session=session)])

    with caplog.at_level(logging.WARNING, logger="kliz"):
        indexer.notify_many(["https://a.example/1", "https://a.example/2"])

    assert any("2 URL(s) failed" in r.getMessage() for r in caplog.records)


def test_api_key_never_appears_in_logs_errors_or_results(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    session = make_mock_session()
    key_location = f"https://a.example/{SECRET}.txt"
    provider = IndexNowProvider(
        api_key=SECRET, key_location=key_location, session=session
    )
    indexer = Kliz([provider], max_attempts=3, sleep=lambda _: None)
    texts: list[str] = []

    with caplog.at_level(logging.DEBUG, logger="kliz"):
        # Success, HTTP failures with retry, network failure.
        session.post.return_value = Mock(status_code=200)
        results = indexer.notify_many_detailed(["https://a.example/1"])
        session.post.return_value = Mock(status_code=503, headers={"Retry-After": "1"})
        results |= indexer.notify_many_detailed(["https://a.example/2"])
        session.post.side_effect = requests.ConnectionError(f"boom {SECRET}?")
        results |= indexer.notify_many_detailed(["https://a.example/3"])
        session.post.side_effect = None
        # Every verify_key outcome.
        for response in [
            Mock(status_code=200, text=SECRET, headers={}),
            Mock(status_code=404, text="", headers={}),
            Mock(status_code=308, text="", headers={"Location": key_location}),
            Mock(status_code=200, text="<html>", headers={"Content-Type": "text/html"}),
            Mock(status_code=200, text="other", headers={}),
        ]:
            session.get.return_value = response
            try:
                provider.verify_key()
            except ProviderError as exc:
                texts.append(str(exc))

    texts += [r.getMessage() for r in caplog.records]
    texts += [str(r) for rs in results.values() for r in rs]
    assert len(caplog.records) > 5
    assert not [text for text in texts if SECRET in text]


def test_cli_verbose_flags_set_log_level(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    kliz_logger = logging.getLogger("kliz")
    sitemap = tmp_path / "s.xml"
    sitemap.write_text(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://a.example/</loc></url></urlset>"
    )

    try:
        assert main(["-v", "notify", "--sitemap", str(sitemap), "--dry-run"]) == 0
        assert kliz_logger.level == logging.INFO
        assert "INFO kliz.sitemap: read 1 page URL(s)" in capsys.readouterr().err

        assert main(["-vv", "notify", "--sitemap", str(sitemap), "--dry-run"]) == 0
        assert kliz_logger.level == logging.DEBUG
        assert "DEBUG kliz.sitemap: reading sitemap" in capsys.readouterr().err
        assert len([h for h in kliz_logger.handlers if h.get_name() == "kliz-cli"]) == 1

        assert main(["notify", "--sitemap", str(sitemap), "--dry-run"]) == 0
        assert "kliz.sitemap" not in capsys.readouterr().err
        assert not [h for h in kliz_logger.handlers if h.get_name() == "kliz-cli"]
    finally:
        kliz_logger.setLevel(logging.NOTSET)


def test_read_sitemap_logs_are_quiet_by_default(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    sitemap = tmp_path / "s.xml"
    sitemap.write_text("<urlset><url><loc>https://a.example/</loc></url></urlset>")

    with caplog.at_level(logging.WARNING, logger="kliz"):
        read_sitemap(sitemap)

    assert caplog.records == []
