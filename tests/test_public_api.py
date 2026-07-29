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