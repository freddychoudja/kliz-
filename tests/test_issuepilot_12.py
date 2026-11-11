"""Reject invalid hostnames before providers receive a normalized URL."""

import pytest

from kliz import normalize_url
from kliz._validation import parse_http_url
from kliz.providers import IndexNowProvider


@pytest.mark.parametrize(
    "url",
    [
        "http://exa mple.com/",
        "http://./",
        "http://a..com/",
        "http://%41.com/",
        "http://a.com%2f.evil.com/",
        "http://exa\nmple.com/",
        "http://exa\tmple.com/",
        "http://example.com../",
        "http://" + "a" * 64 + ".example/",
    ],
)
def test_invalid_hosts_are_rejected_by_all_validation_entry_points(url: str) -> None:
    provider = IndexNowProvider(api_key="abcdefgh")
    try:
        for validate in (parse_http_url, normalize_url, provider.validate_url):
            with pytest.raises(ValueError):
                validate(url)
    finally:
        provider.close()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("HTTPS://Example.COM./p", "https://example.com/p"),
        ("https://Bücher.example/", "https://xn--bcher-kva.example/"),
        ("http://127.0.0.1:80/", "http://127.0.0.1/"),
        ("http://[2001:db8::1]:80/", "http://[2001:db8::1]/"),
        ("https://service_name.example/", "https://service_name.example/"),
    ],
)
def test_valid_hostname_forms_remain_supported(url: str, expected: str) -> None:
    assert normalize_url(url) == expected
    assert normalize_url(expected) == expected
