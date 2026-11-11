"""Search Console derives its default only from a resolved sitemap URL."""

from pathlib import Path

import pytest

from kliz.cli import ConfigurationError, _build_indexer, _build_parser


@pytest.mark.parametrize(
    ("sitemap", "configured", "explicit", "expected"),
    [
        ("http-sitemap.xml", None, None, "https://example.com/sitemap.xml"),
        (
            None,
            "https://example.com/config.xml",
            None,
            "https://example.com/config.xml",
        ),
        (None, "http-sitemap.xml", None, "https://example.com/sitemap.xml"),
        (
            "https://example.com/flag.xml",
            "https://example.com/config.xml",
            None,
            "https://example.com/flag.xml",
        ),
        (
            "http-sitemap.xml",
            "https://example.com/config.xml",
            None,
            "https://example.com/sitemap.xml",
        ),
        (
            None,
            "https://example.com/config.xml",
            "https://example.com/explicit.xml",
            "https://example.com/explicit.xml",
        ),
    ],
)
def test_resolved_sitemap_controls_the_search_console_default(
    tmp_path: Path,
    sitemap: str | None,
    configured: str | None,
    explicit: str | None,
    expected: str,
) -> None:
    account = tmp_path / "account.json"
    account.write_text("{}", encoding="utf-8")
    config = {
        "gsc_site": "https://example.com/",
        "gsc_service_account_file": str(account),
    }
    if configured is not None:
        config["sitemap"] = configured
    args = ["notify"]
    if sitemap is not None:
        args.extend(["--sitemap", sitemap])
    if explicit is not None:
        args[:0] = ["--gsc-sitemap", explicit]
    parsed = _build_parser(config).parse_args(args)
    try:
        indexer = _build_indexer(parsed)
    except ConfigurationError as exc:
        pytest.fail(f"A local sitemap filename is not a remote sitemap URL: {exc}")
    (provider,) = indexer.providers
    assert provider.sitemap_url == expected
