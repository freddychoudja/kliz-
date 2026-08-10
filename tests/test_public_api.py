"""Tests for package metadata and shared validation."""

import pytest

import kliz
from kliz._validation import parse_http_url


def test_public_version_is_loaded_from_distribution_metadata() -> None:
    assert kliz.__version__ == "0.1.0"


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
