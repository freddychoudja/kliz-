"""Tests for the kliz CLI."""

from __future__ import annotations

import argparse
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from kliz import NotificationResult
from kliz.cli import ConfigurationError, main


def test_main_version(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("kliz.cli.__version__", "0.1.0"):
        exit_code = main(["--version"])

    assert exit_code == 0
    assert "0.1.0" in capsys.readouterr().out


def test_main_help(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--help"])

    assert exit_code == 0
    assert "notify" in capsys.readouterr().out


def test_notify_no_providers_gives_config_error() -> None:
    exit_code = main(["notify", "https://example.com/page"])
    assert exit_code == 2


def test_notify_no_url_or_batch_gives_config_error() -> None:
    exit_code = main(["notify"])
    assert exit_code == 2


def test_providers_no_config_gives_config_error() -> None:
    exit_code = main(["providers"])
    assert exit_code == 2


def test_notify_missing_google_service_account_file() -> None:
    exit_code = main(
        [
            "--google-service-account-file",
            "/missing/key.json",
            "notify",
            "https://example.com/page",
        ],
    )
    assert exit_code == 2


def test_notify_indexnow_missing_key_location() -> None:
    exit_code = main(
        [
            "--indexnow-api-key",
            "abcdefgh",
            "notify",
            "https://example.com/page",
        ],
    )
    assert exit_code == 2


def test_notify_success(capsys: pytest.CaptureFixture[str]) -> None:
    mock_indexer = MagicMock()
    mock_indexer.notify_all_detailed.return_value = {
        "IndexNowProvider": NotificationResult(
            provider="IndexNowProvider",
            success=True,
        ),
    }
    with patch("kliz.cli.Kliz", return_value=mock_indexer):
        exit_code = main(
            [
                "--indexnow-api-key",
                "abcdefgh",
                "--indexnow-key-location",
                "https://example.com/key.txt",
                "notify",
                "https://example.com/page",
            ],
        )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "https://example.com/page" in output
    assert "OK" in output


def test_notify_failure(capsys: pytest.CaptureFixture[str]) -> None:
    mock_indexer = MagicMock()
    mock_indexer.notify_all_detailed.return_value = {
        "IndexNowProvider": NotificationResult(
            provider="IndexNowProvider",
            success=False,
            retryable=True,
            error="temporary failure",
            status_code=429,
        ),
    }
    with patch("kliz.cli.Kliz", return_value=mock_indexer):
        exit_code = main(
            [
                "--indexnow-api-key",
                "abcdefgh",
                "--indexnow-key-location",
                "https://example.com/key.txt",
                "notify",
                "https://example.com/page",
            ],
        )

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "❌" in err
    assert "temporary failure" in err


def test_notify_batch(capsys: pytest.CaptureFixture[str]) -> None:
    mock_indexer = MagicMock()
    mock_indexer.notify_all_detailed.return_value = {
        "IndexNowProvider": NotificationResult(
            provider="IndexNowProvider",
            success=True,
        ),
    }
    with patch("kliz.cli.Kliz", return_value=mock_indexer):
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
        ) as fh:
            fh.write("# sitemap\nhttps://example.com/a\nhttps://example.com/b\n")
            path = fh.name
        exit_code = main(
            [
                "--indexnow-api-key",
                "abcdefgh",
                "--indexnow-key-location",
                "https://example.com/key.txt",
                "notify",
                "--batch",
                path,
            ],
        )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "https://example.com/a" in output
    assert "https://example.com/b" in output


def test_notify_batch_empty_file_gives_config_error() -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
    ) as fh:
        fh.write("")
        path = fh.name
    exit_code = main(
        [
            "--indexnow-api-key",
            "abcdefgh",
            "--indexnow-key-location",
            "https://example.com/key.txt",
            "notify",
            "--batch",
            path,
        ],
    )
    assert exit_code == 2


def test_providers_list(capsys: pytest.CaptureFixture[str]) -> None:
    from kliz.providers import IndexNowProvider

    provider = IndexNowProvider(
        api_key="abcdefgh",
        key_location="https://example.com/key.txt",
    )
    mock_indexer = MagicMock()
    mock_indexer.providers = [provider]
    with patch("kliz.cli._build_indexer", return_value=mock_indexer):
        exit_code = main(["providers"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "IndexNowProvider" in output


def test_read_urls_from_file() -> None:
    from kliz.cli import _read_urls_from_file

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
    ) as fh:
        fh.write("# comment\nhttps://example.com/a\n\nhttps://example.com/b\n")
        path = fh.name

    urls = _read_urls_from_file(path)
    assert urls == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_read_urls_from_file_missing() -> None:
    from kliz.cli import _read_urls_from_file

    with pytest.raises(ConfigurationError, match="cannot read"):
        _read_urls_from_file("/missing/file.txt")


def test_resolve_urls_single() -> None:
    from kliz.cli import _resolve_urls

    args = argparse.Namespace(url="https://example.com/a", batch=None)
    assert _resolve_urls(args) == ["https://example.com/a"]


def test_resolve_urls_batch() -> None:
    from kliz.cli import _resolve_urls

    args = argparse.Namespace(url=None, batch="/some/file.txt")
    with patch("kliz.cli._read_urls_from_file", return_value=["https://example.com/a"]):
        assert _resolve_urls(args) == ["https://example.com/a"]


def test_resolve_urls_none_gives_config_error() -> None:
    from kliz.cli import _resolve_urls

    args = argparse.Namespace(url=None, batch=None)
    with pytest.raises(ConfigurationError, match="provide a URL"):
        _resolve_urls(args)


def test_build_indexer_creates_indexnow() -> None:
    from kliz.cli import _build_indexer

    args = argparse.Namespace(
        indexnow_api_key="abcdefgh",
        indexnow_key_location="https://example.com/key.txt",
        google_service_account_file=None,
    )
    indexer = _build_indexer(args)
    assert len(indexer.providers) == 1
    assert indexer.providers[0].__class__.__name__ == "IndexNowProvider"


def test_build_indexer_requires_key_location() -> None:
    from kliz.cli import _build_indexer

    args = argparse.Namespace(
        indexnow_api_key="abcdefgh",
        indexnow_key_location=None,
        google_service_account_file=None,
    )
    with pytest.raises(ConfigurationError, match="key-location"):
        _build_indexer(args)


def test_build_indexer_creates_google() -> None:
    from kliz.cli import _build_indexer

    args = argparse.Namespace(
        indexnow_api_key=None,
        indexnow_key_location=None,
        google_service_account_file="/dev/null",
    )
    indexer = _build_indexer(args)
    assert len(indexer.providers) == 1
    assert indexer.providers[0].__class__.__name__ == "GoogleProvider"


def test_build_indexer_no_providers_gives_config_error() -> None:
    from kliz.cli import _build_indexer

    args = argparse.Namespace(
        indexnow_api_key=None,
        indexnow_key_location=None,
        google_service_account_file=None,
    )
    with pytest.raises(ConfigurationError, match="no providers configured"):
        _build_indexer(args)
