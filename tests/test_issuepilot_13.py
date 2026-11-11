"""URL-prefix properties use canonical authority syntax in API requests."""

from unittest.mock import Mock

import pytest

from kliz.providers import GoogleSearchConsoleProvider


@pytest.mark.parametrize(
    ("site", "expected"),
    [
        ("https://[::1]:8443/", "https://[::1]:8443/"),
        ("https://[::1]:443/blog", "https://[::1]/blog/"),
        ("HTTPS://Example.com:443/", "https://example.com/"),
        ("http://Example.com:80/blog", "http://example.com/blog/"),
        ("https://example.com:8443/blog", "https://example.com:8443/blog/"),
        ("sc-domain:Example.COM.", "sc-domain:example.com"),
    ],
)
def test_property_authority_and_default_sitemap_are_normalized(
    site: str, expected: str
) -> None:
    try:
        provider = GoogleSearchConsoleProvider("account.json", site)
    except ValueError as exc:
        pytest.fail(f"Valid URL-prefix property must be accepted: {exc}")
    assert provider.site_url == expected
    root = "https://example.com/" if expected.startswith("sc-domain:") else expected
    assert provider.sitemap_url == root + "sitemap.xml"


@pytest.mark.parametrize(
    "site", ["https://example.com:0/x", "http://example.com:0/", "http://[::1]:0/"]
)
def test_zero_property_port_is_rejected_as_a_property_error(site: str) -> None:
    with pytest.raises(ValueError, match="port"):
        GoogleSearchConsoleProvider("account.json", site)


def test_api_request_uses_the_normalized_ipv6_property(
    google_client_mocks: dict[str, Mock],
) -> None:
    try:
        provider = GoogleSearchConsoleProvider(
            "account.json", "https://[::1]:8443/blog"
        )
    except ValueError as exc:
        pytest.fail(f"Valid IPv6 URL-prefix property must be accepted: {exc}")
    assert provider.notify("https://[::1]:8443/blog/page") is True
    service = google_client_mocks["build"].return_value
    service.sitemaps.return_value.submit.assert_called_once_with(
        siteUrl="https://[::1]:8443/blog/",
        feedpath="https://[::1]:8443/blog/sitemap.xml",
    )
