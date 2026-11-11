"""Tests for package metadata and shared validation."""

import re
from pathlib import Path

import pytest

import kliz
from kliz._validation import parse_http_url


def test_public_version_is_loaded_from_distribution_metadata() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    match = re.search(r'^version = "([^"]+)"', pyproject.read_text(), re.MULTILINE)

    assert match is not None
    assert kliz.__version__ == match.group(1)


def test_public_api_exports_batch_provider() -> None:
    assert "BatchProvider" in kliz.__all__
    assert kliz.BatchProvider is not None


@pytest.mark.parametrize(
    "url",
    [None, 42, "", "mailto:test@example.com", "https:///page", "https://u:p@x.com"],
)
def test_shared_url_validation_rejects_invalid_values(url: object) -> None:
    with pytest.raises(ValueError):
        parse_http_url(url)  # type: ignore[arg-type]


def test_shared_url_validation_returns_parsed_url() -> None:
    parsed = parse_http_url("  HTTPS://Example.com/page  ")

    assert parsed.scheme.lower() == "https"
    assert parsed.hostname == "example.com"
    assert parsed.path == "/page"


def test_shared_url_validation_always_rejects_fragments() -> None:
    with pytest.raises(ValueError, match="fragment"):
        parse_http_url("https://example.com/page#reviews")


def test_shared_url_validation_allows_query_strings_by_default() -> None:
    parsed = parse_http_url("https://example.com/page?utm_source=newsletter")

    assert parsed.path == "/page"
    assert parsed.query == "utm_source=newsletter"


def test_shared_url_validation_rejects_query_strings_in_clean_mode() -> None:
    with pytest.raises(ValueError, match="query"):
        parse_http_url("https://example.com/page?id=77", require_clean=True)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("HTTPS://Example.COM:443", "https://example.com/"),
        ("  http://a.example:80/x?b=2&a=1  ", "http://a.example/x?b=2&a=1"),
        ("https://a.example:8443/Case/Path", "https://a.example:8443/Case/Path"),
        ("https://a.example./p", "https://a.example/p"),
        ("https://Bücher.example/Straße", "https://xn--bcher-kva.example/Stra%C3%9Fe"),
        (
            "https://a.example/a b?q=café&x=%2F",
            "https://a.example/a%20b?q=caf%C3%A9&x=%2F",
        ),
        ("http://[::1]:80/", "http://[::1]/"),
        ("http://[2001:DB8::1]:80/", "http://[2001:db8::1]/"),
        ("http://127.0.0.1:80/", "http://127.0.0.1/"),
        ("HTTPS://Example.COM./p", "https://example.com/p"),
        ("https://service_name.example/", "https://service_name.example/"),
        ("https://a.example?x=1", "https://a.example/?x=1"),
    ],
)
def test_normalize_url(url: str, expected: str) -> None:
    assert kliz.normalize_url(url) == expected
    assert kliz.normalize_url(expected) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://a.example/#top",
        "ftp://a.example/",
        "https://a.example:99999/",
        "http://[1::2::3]/",
        "https://" + "é" * 70 + ".example/",
    ],
)
def test_normalize_url_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(ValueError):
        kliz.normalize_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://exa mple.com/",
        "http://exa\nmple.com/",
        "http://exa\tmple.com/",
        "http://exa mple.com/",
        "http://./",
        "http://a..com/",
        "http://example.com../",
        "http://%41.com/",
        "http://a.com%2f.evil.com/",
        "http://a,b.com/",
        "http://*.example.com/",
        "http://" + "a" * 64 + ".example/",
        "http://" + ".".join(["a" * 63] * 4) + ".example/",
        "http://[fe80::1%25eth0]/",
    ],
)
def test_invalid_hostnames_are_rejected_everywhere(url: str) -> None:
    provider = kliz.IndexNowProvider(api_key="abcdefgh")
    try:
        for validate in (parse_http_url, kliz.normalize_url, provider.validate_url):
            with pytest.raises(ValueError, match="hostname"):
                validate(url)
    finally:
        provider.close()


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("http://a..com/", "url has an invalid hostname"),
        ("http://" + "a" * 64 + ".example/", "url has an invalid hostname"),
        (
            "https://" + "é" * 70 + ".example/",
            "url has an invalid internationalized hostname",
        ),
    ],
)
def test_hostname_errors_only_mention_idn_for_non_ascii_hosts(
    url: str, message: str
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        parse_http_url(url)
