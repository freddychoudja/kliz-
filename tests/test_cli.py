"""Tests for the kliz CLI."""

from __future__ import annotations

import argparse
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kliz import IndexNowProvider, NotificationResult, ProviderError, SitemapError
from kliz.cli import ConfigurationError, main
from kliz.providers import GoogleSearchConsoleProvider


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
    mock_indexer.notify_many_detailed.return_value = {
        "IndexNowProvider": [
            NotificationResult(
                provider="IndexNowProvider",
                success=True,
                urls=("https://example.com/page",),
            ),
        ],
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
    mock_indexer.notify_many_detailed.return_value = {
        "IndexNowProvider": [
            NotificationResult(
                provider="IndexNowProvider",
                success=False,
                retryable=True,
                error="temporary failure",
                status_code=429,
                urls=("https://example.com/page",),
            ),
        ],
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
    mock_indexer.notify_many_detailed.return_value = {
        "IndexNowProvider": [
            NotificationResult(
                provider="IndexNowProvider",
                success=True,
                urls=("https://example.com/a", "https://example.com/b"),
            ),
        ],
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
    mock_indexer.notify_many_detailed.assert_called_once_with(
        ["https://example.com/a", "https://example.com/b"]
    )
    mock_indexer.notify_all_detailed.assert_not_called()
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
        fh.write(
            "# comment\nhttps://example.com/a\n\n  # indented\nhttps://example.com/b\n"
        )
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
        gsc_site=None,
        max_attempts=1,
        allow_query=False,
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
        gsc_site=None,
        max_attempts=1,
        allow_query=False,
    )
    with pytest.raises(ConfigurationError, match="key-location"):
        _build_indexer(args)


def test_build_indexer_creates_google() -> None:
    from kliz.cli import _build_indexer

    args = argparse.Namespace(
        indexnow_api_key=None,
        indexnow_key_location=None,
        google_service_account_file="/dev/null",
        gsc_site=None,
        max_attempts=1,
        allow_query=False,
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
        gsc_site=None,
        max_attempts=1,
        allow_query=False,
    )
    with pytest.raises(ConfigurationError, match="no providers configured"):
        _build_indexer(args)


def test_notify_batch_reports_partial_failures(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_indexer = MagicMock()
    mock_indexer.notify_many_detailed.return_value = {
        "IndexNowProvider": [
            NotificationResult(
                provider="IndexNowProvider",
                success=False,
                error="url must not contain a query string",
                urls=("https://example.com/b?x=1",),
            ),
            NotificationResult(
                provider="IndexNowProvider",
                success=True,
                urls=("https://example.com/a",),
            ),
        ],
    }
    with patch("kliz.cli.Kliz", return_value=mock_indexer):
        exit_code = main(
            [
                "--indexnow-api-key",
                "abcdefgh",
                "--indexnow-key-location",
                "https://example.com/key.txt",
                "notify",
                "https://example.com/a",
            ],
        )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "✅ https://example.com/a → IndexNowProvider: OK" in captured.out
    assert "❌ https://example.com/b?x=1 → IndexNowProvider" in captured.err
    assert "query string" in captured.err


def test_indexnow_keygen_prints_only_the_key_on_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["indexnow", "keygen", "--length", "16"])

    assert exit_code == 0
    captured = capsys.readouterr()
    key = captured.out.strip()
    assert len(key) == 16 and key.isalnum()
    assert captured.err == ""


def test_indexnow_keygen_writes_key_file_and_prints_next_steps(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        ["indexnow", "keygen", "--write", str(tmp_path), "--site", "https://a.example"]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    key = captured.out.strip()
    assert (tmp_path / f"{key}.txt").read_text(encoding="utf-8") == key
    assert f"https://a.example/{key}.txt" in captured.err
    assert f"KLIZ_INDEXNOW_API_KEY={key}" in captured.err


@pytest.mark.parametrize(
    "extra",
    [["--length", "4"], ["--site", "ftp://a.example"], ["--write", "/nonexistent/dir"]],
)
def test_indexnow_keygen_invalid_options_give_config_error(extra: list[str]) -> None:
    assert main(["indexnow", "keygen", *extra]) == 2


def test_indexnow_verify_key_success(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(
        IndexNowProvider,
        "verify_key",
        return_value="https://a.example/abcdefgh.txt",
    ) as verify:
        exit_code = main(
            [
                "--indexnow-api-key",
                "abcdefgh",
                "indexnow",
                "verify-key",
                "--site",
                "https://a.example",
            ]
        )

    assert exit_code == 0
    verify.assert_called_once_with("https://a.example")
    assert "✅ https://a.example/abcdefgh.txt" in capsys.readouterr().out


def test_indexnow_verify_key_failure_exits_1(
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = ProviderError("returned an HTML page", provider="IndexNowProvider")
    with patch.object(IndexNowProvider, "verify_key", side_effect=error):
        exit_code = main(
            [
                "--indexnow-api-key",
                "abcdefgh",
                "--indexnow-key-location",
                "https://a.example/abcdefgh.txt",
                "indexnow",
                "verify-key",
            ]
        )

    assert exit_code == 1
    assert "HTML page" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["indexnow", "verify-key", "--site", "https://a.example"],
        ["--indexnow-api-key", "abcdefgh", "indexnow", "verify-key"],
        ["--indexnow-api-key", "bad", "indexnow", "verify-key", "--site", "https://a"],
    ],
)
def test_indexnow_verify_key_config_errors(
    argv: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KLIZ_INDEXNOW_API_KEY", raising=False)
    monkeypatch.delenv("KLIZ_INDEXNOW_KEY_LOCATION", raising=False)

    assert main(argv) == 2


INDEXNOW_ARGS = [
    "--indexnow-api-key",
    "abcdefgh",
    "--indexnow-key-location",
    "https://example.com/key.txt",
]


def test_notify_sitemap_sends_its_urls() -> None:
    urls = ["https://example.com/a", "https://example.com/b"]
    mock_indexer = MagicMock()
    mock_indexer.notify_many_detailed.return_value = {}
    with (
        patch("kliz.cli.read_sitemap", return_value=urls) as read,
        patch("kliz.cli.Kliz", return_value=mock_indexer),
    ):
        exit_code = main(
            [
                *INDEXNOW_ARGS,
                "notify",
                "--sitemap",
                "https://example.com/sitemap.xml",
                "--since",
                "2026-10-01",
            ]
        )

    assert exit_code == 0
    read.assert_called_once_with(
        "https://example.com/sitemap.xml", since=datetime(2026, 10, 1)
    )
    mock_indexer.notify_many_detailed.assert_called_once_with(urls)


def test_notify_dry_run_prints_urls_without_providers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        patch("kliz.cli.read_sitemap", return_value=["https://example.com/a"]),
        patch("kliz.cli.Kliz") as kliz,
    ):
        exit_code = main(
            ["notify", "--sitemap", "https://example.com/sitemap.xml", "--dry-run"]
        )

    assert exit_code == 0
    kliz.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == "https://example.com/a\n"
    assert "1 URL(s), nothing sent" in captured.err


def test_notify_sitemap_with_nothing_new_succeeds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("kliz.cli.read_sitemap", return_value=[]):
        exit_code = main(
            [*INDEXNOW_ARGS, "notify", "--sitemap", "s.xml", "--since", "2026-10-01"]
        )

    assert exit_code == 0
    assert "nothing changed since 2026-10-01" in capsys.readouterr().err


@pytest.mark.parametrize(
    "notify_args",
    [
        ["--sitemap", "s.xml"],
        ["--sitemap", "s.xml", "--since", "last week"],
        ["--since", "2026-10-01", "https://example.com/a"],
        ["--sitemap", "s.xml", "https://example.com/a"],
        ["--sitemap", "s.xml", "--batch", "urls.txt"],
    ],
)
def test_notify_sitemap_config_errors(notify_args: list[str]) -> None:
    with patch("kliz.cli.read_sitemap", return_value=[]):
        assert main([*INDEXNOW_ARGS, "notify", *notify_args]) == 2


def test_notify_sitemap_errors_exit_1(capsys: pytest.CaptureFixture[str]) -> None:
    error = SitemapError("s.xml: returned an HTML page, not a sitemap")
    with patch("kliz.cli.read_sitemap", side_effect=error):
        assert main([*INDEXNOW_ARGS, "notify", "--sitemap", "s.xml"]) == 1
    assert "HTML page" in capsys.readouterr().err


def _gsc_args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "indexnow_api_key": None,
        "indexnow_key_location": None,
        "google_service_account_file": None,
        "gsc_site": "https://example.com/",
        "gsc_sitemap": None,
        "gsc_service_account_file": "/dev/null",
        "max_attempts": 1,
        "allow_query": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


@pytest.mark.parametrize(
    ("overrides", "expected_sitemap"),
    [
        ({}, "https://example.com/sitemap.xml"),
        ({"sitemap": "https://example.com/s.xml"}, "https://example.com/s.xml"),
        ({"sitemap": "local-sitemap.xml"}, "https://example.com/sitemap.xml"),
        ({"gsc_sitemap": ""}, "https://example.com/sitemap.xml"),
        (
            {
                "sitemap": "https://example.com/s.xml",
                "gsc_sitemap": "https://example.com/g.xml",
            },
            "https://example.com/g.xml",
        ),
    ],
)
def test_build_indexer_creates_search_console(
    overrides: dict[str, object], expected_sitemap: str
) -> None:
    from kliz.cli import _build_indexer

    indexer = _build_indexer(_gsc_args(**overrides))

    (provider,) = indexer.providers
    assert isinstance(provider, GoogleSearchConsoleProvider)
    assert provider.site_url == "https://example.com/"
    assert provider.sitemap_url == expected_sitemap


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"gsc_service_account_file": None}, "--gsc-service-account-file is required"),
        ({"gsc_service_account_file": "/nonexistent/sa.json"}, "not found"),
        ({"gsc_site": "ftp://example.com"}, "Search Console: "),
        ({"gsc_sitemap": "https://other.example/s.xml"}, "sitemap_url is invalid"),
    ],
)
def test_build_indexer_search_console_config_errors(
    overrides: dict[str, object], message: str
) -> None:
    from kliz.cli import _build_indexer

    with pytest.raises(ConfigurationError, match=message):
        _build_indexer(_gsc_args(**overrides))


def test_gsc_options_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from kliz.cli import _build_parser

    monkeypatch.setenv("KLIZ_GSC_SITE", "sc-domain:example.com")
    monkeypatch.setenv("KLIZ_GSC_SITEMAP", "https://example.com/s.xml")
    monkeypatch.setenv("KLIZ_GSC_SERVICE_ACCOUNT_FILE", "/secrets/sa.json")

    args = _build_parser().parse_args(["providers"])

    assert args.gsc_site == "sc-domain:example.com"
    assert args.gsc_sitemap == "https://example.com/s.xml"
    assert args.gsc_service_account_file == "/secrets/sa.json"


def test_max_attempts_reaches_the_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kliz.cli import _build_indexer, _build_parser

    monkeypatch.setenv("KLIZ_MAX_ATTEMPTS", "4")
    args = _build_parser().parse_args(
        [*INDEXNOW_ARGS, "notify", "https://example.com/a"]
    )
    assert args.max_attempts == 4

    args = _build_parser().parse_args(
        [*INDEXNOW_ARGS, "--max-attempts", "2", "notify", "https://example.com/a"]
    )
    assert _build_indexer(args).max_attempts == 2


def test_invalid_max_attempts_is_a_configuration_error() -> None:
    assert main([*INDEXNOW_ARGS, "--max-attempts", "0", "providers"]) == 2


def test_non_numeric_max_attempts_env_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KLIZ_MAX_ATTEMPTS", "lots")

    assert main([*INDEXNOW_ARGS, "providers"]) == 2


def test_allow_query_flag_reaches_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    from kliz.cli import _build_indexer, _build_parser

    args = _build_parser().parse_args([*INDEXNOW_ARGS, "--allow-query", "providers"])
    (provider,) = _build_indexer(args).providers
    assert isinstance(provider, IndexNowProvider) and provider.allow_query is True

    monkeypatch.setenv("KLIZ_ALLOW_QUERY", "true")
    assert _build_parser().parse_args(["providers"]).allow_query is True
    monkeypatch.setenv("KLIZ_ALLOW_QUERY", "false")
    assert _build_parser().parse_args(["providers"]).allow_query is False
