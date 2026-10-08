"""Tests for CLI settings files, precedence, JSON output and stdin."""

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kliz import NotificationResult
from kliz._config import ConfigurationError, find_config, load_config
from kliz.cli import _build_indexer, _build_parser, main

KEY_ARGS = [
    "--indexnow-api-key",
    "abcdefgh",
    "--indexnow-key-location",
    "https://a.example/key.txt",
]


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run each test in an empty directory without KLIZ_* variables."""

    monkeypatch.chdir(tmp_path)
    for name in [
        "KLIZ_INDEXNOW_API_KEY",
        "KLIZ_INDEXNOW_KEY_LOCATION",
        "KLIZ_MAX_ATTEMPTS",
        "KLIZ_TIMEOUT",
        "KLIZ_ALLOW_QUERY",
        "KLIZ_GSC_SITE",
    ]:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def test_find_config_prefers_kliz_toml_then_pyproject(tmp_path: Path) -> None:
    assert find_config(None, tmp_path) is None
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'site'\n")
    assert find_config(None, tmp_path) == tmp_path / "pyproject.toml"
    (tmp_path / "kliz.toml").write_text("")
    assert find_config(None, tmp_path) == tmp_path / "kliz.toml"
    assert find_config("kliz.toml", tmp_path) == Path("kliz.toml")
    with pytest.raises(ConfigurationError, match="not found"):
        find_config("missing.toml", tmp_path)


def test_load_config_reads_both_layouts_and_key_styles(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'site'\n")
    assert load_config(pyproject) == {}

    pyproject.write_text(
        "[tool.kliz]\nsitemap = 'https://a.example/s.xml'\nmax-attempts = 3\n"
        "allow_query = true\ntimeout = 7\n"
    )
    assert load_config(pyproject) == {
        "sitemap": "https://a.example/s.xml",
        "max_attempts": 3,
        "allow_query": True,
        "timeout": 7,
    }

    standalone = tmp_path / "kliz.toml"
    standalone.write_text("gsc-site = 'sc-domain:a.example'\ntimeout = 2.5\n")
    assert load_config(standalone) == {
        "gsc_site": "sc-domain:a.example",
        "timeout": 2.5,
    }


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("sitemaps = 'x'", "unknown setting 'sitemaps'"),
        ("max-attempts = '3'", "max-attempts must be an integer$"),
        ("max-attempts = true", "max-attempts must be an integer$"),
        ("allow-query = 'yes'", "allow-query must be a boolean$"),
        ("timeout = 'fast'", "timeout must be an integer or number$"),
        ("sitemap = [", "cannot read"),
    ],
)
def test_load_config_rejects_bad_settings(
    tmp_path: Path, content: str, message: str
) -> None:
    path = tmp_path / "kliz.toml"
    path.write_text(content)

    with pytest.raises(ConfigurationError, match=message):
        load_config(path)


def test_load_config_rejects_non_table_section(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text("[tool]\nkliz = 'oops'\n")

    with pytest.raises(ConfigurationError, match=r"\[tool.kliz\] must be a table"):
        load_config(path)


def test_settings_precedence_flag_over_env_over_config(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (isolated / "kliz.toml").write_text(
        "max-attempts = 2\ntimeout = 5\nallow-query = true\n"
        "indexnow-key-location = 'https://a.example/from-config.txt'\n"
    )

    def parse(*extra: str) -> object:
        from kliz.cli import _load_cli_config

        args = [*extra, "providers"]
        return _build_parser(_load_cli_config(args)).parse_args(args)

    args = parse()
    assert (args.max_attempts, args.timeout, args.allow_query) == (2, 5, True)
    assert args.indexnow_key_location == "https://a.example/from-config.txt"

    monkeypatch.setenv("KLIZ_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("KLIZ_ALLOW_QUERY", "false")
    args = parse()
    assert (args.max_attempts, args.allow_query) == (4, False)

    args = parse("--max-attempts", "6", "--timeout", "1.5", "--allow-query")
    assert (args.max_attempts, args.timeout, args.allow_query) == (6, 1.5, True)


def test_explicit_config_and_errors_exit_2(
    isolated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (isolated / "site.toml").write_text("max-attempts = 'x'\n")

    assert main(["--config", "missing.toml", "providers"]) == 2
    assert main(["--config", "site.toml", "providers"]) == 2
    assert "max-attempts must be an integer" in capsys.readouterr().err


def test_config_values_build_providers_with_timeout(isolated: Path) -> None:
    (isolated / "kliz.toml").write_text(
        "indexnow-api-key = 'abcdefgh'\n"
        "indexnow-key-location = 'https://a.example/abcdefgh.txt'\n"
        "timeout = 3\n"
    )

    assert main(["providers"]) == 0
    from kliz.cli import _load_cli_config

    args = _build_parser(_load_cli_config(["providers"])).parse_args(["providers"])
    (provider,) = _build_indexer(args).providers
    assert provider.timeout == 3  # type: ignore[attr-defined]


def test_invalid_provider_settings_exit_2(
    isolated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (isolated / "kliz.toml").write_text(
        "indexnow-api-key = 'short'\nindexnow-key-location = 'https://a.example/k.txt'\n"
    )

    assert main(["providers"]) == 2
    assert "IndexNow: api_key must contain" in capsys.readouterr().err
    assert main([*KEY_ARGS, "--timeout", "0", "providers"]) == 2


def test_config_sitemap_is_used_only_without_another_source(isolated: Path) -> None:
    (isolated / "kliz.toml").write_text("sitemap = 'https://a.example/s.xml'\n")

    with patch("kliz.cli.read_sitemap", return_value=["https://a.example/"]) as read:
        assert main(["notify", "--dry-run", "--since", "2026-01-01"]) == 0
        assert main(["--timeout", "4", "notify", "--dry-run"]) == 0
        assert main(["notify", "https://a.example/x", "--dry-run"]) == 0

    assert [c.args[0] for c in read.call_args_list] == [
        "https://a.example/s.xml",
        "https://a.example/s.xml",
    ]
    assert read.call_args_list[1].kwargs["timeout"] == 4


def test_urls_can_come_from_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for argv in (["notify", "-", "--dry-run"], ["notify", "--batch", "-", "--dry-run"]):
        monkeypatch.setattr(
            "sys.stdin", io.StringIO("https://a/1\n  # c\n\nhttps://a/2\n")
        )
        assert main(argv) == 0
        assert capsys.readouterr().out == "https://a/1\nhttps://a/2\n"

    monkeypatch.setattr("sys.stdin", io.StringIO("# only comments\n"))
    assert main(["notify", "-", "--dry-run"]) == 2
    assert "no URLs found in stdin" in capsys.readouterr().err


def test_json_report_for_a_real_run(capsys: pytest.CaptureFixture[str]) -> None:
    indexer = MagicMock()
    indexer.notify_many_detailed.return_value = {
        "IndexNowProvider": [
            NotificationResult(
                provider="IndexNowProvider",
                success=False,
                retryable=True,
                error="HTTP 429",
                status_code=429,
                urls=("https://a.example/1",),
                retry_after=30.0,
                attempts=3,
            )
        ]
    }
    with patch("kliz.cli.Kliz", return_value=indexer):
        exit_code = main([*KEY_ARGS, "notify", "https://a.example/1", "--json"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["ok"] is False
    assert report["dry_run"] is False
    assert report["urls"] == ["https://a.example/1"]
    (result,) = report["results"]["IndexNowProvider"]
    assert result == {
        "provider": "IndexNowProvider",
        "success": False,
        "retryable": True,
        "error": "HTTP 429",
        "status_code": 429,
        "urls": ["https://a.example/1"],
        "retry_after": 30.0,
        "attempts": 3,
    }


def test_json_report_for_dry_runs_and_no_changes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("kliz.cli.read_sitemap", return_value=["https://a.example/"]):
        assert main(["notify", "--sitemap", "s.xml", "--dry-run", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "dry_run": True,
        "urls": ["https://a.example/"],
        "results": {},
    }

    with patch("kliz.cli.read_sitemap", return_value=[]):
        args = ["notify", "--sitemap", "s.xml", "--since", "2026-10-01", "--json"]
        assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["urls"] == []
