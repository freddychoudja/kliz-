"""Unit tests for the built-in indexing providers."""

from typing import Optional
from unittest.mock import Mock, patch

import httplib2
import pytest
import requests
from conftest import make_mock_session
from google.auth.exceptions import TransportError
from googleapiclient.errors import HttpError

from kliz import Kliz
from kliz.exceptions import ProviderError
from kliz.providers.google import GoogleProvider, GoogleSearchConsoleProvider
from kliz.providers.indexnow import IndexNowProvider


@pytest.mark.parametrize("status_code", [200, 202])
def test_indexnow_provider_accepts_success_statuses(status_code: int) -> None:
    session = make_mock_session()
    session.post.return_value.status_code = status_code
    provider = IndexNowProvider(
        api_key="indexnow-key",
        key_location="https://example.com/indexnow-key.txt",
        session=session,
    )

    assert provider.notify("https://example.com/articles/new") is True

    session.post.assert_called_once_with(
        "https://api.indexnow.org/indexnow",
        json={
            "host": "example.com",
            "key": "indexnow-key",
            "keyLocation": "https://example.com/indexnow-key.txt",
            "urlList": ["https://example.com/articles/new"],
        },
        timeout=10.0,
    )


def test_indexnow_provider_submits_multiple_urls() -> None:
    session = make_mock_session()
    session.post.return_value.status_code = 200
    provider = IndexNowProvider(api_key="abcdefgh", session=session)
    urls = [
        "https://example.com/first",
        "https://example.com/second",
    ]

    assert provider.notify_many(urls) is True
    assert session.post.call_args.kwargs["json"]["urlList"] == urls


@pytest.mark.parametrize(
    ("status_code", "retryable"),
    [(400, False), (403, False), (422, False), (429, True), (500, True)],
)
def test_indexnow_provider_classifies_http_errors(
    status_code: int,
    retryable: bool,
) -> None:
    session = make_mock_session()
    session.post.return_value.status_code = status_code
    provider = IndexNowProvider(api_key="abcdefgh", session=session)

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/article")

    assert captured.value.status_code == status_code
    assert captured.value.retryable is retryable
    assert captured.value.provider == "IndexNowProvider"


@pytest.mark.parametrize(
    "exception",
    [requests.Timeout("timeout"), requests.ConnectionError("offline")],
)
def test_indexnow_provider_wraps_transient_network_errors(
    exception: requests.RequestException,
) -> None:
    session = make_mock_session()
    session.post.side_effect = exception
    provider = IndexNowProvider(api_key="abcdefgh", session=session)

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/article")

    assert captured.value.retryable is True
    assert captured.value.status_code is None


def test_indexnow_provider_wraps_other_request_errors() -> None:
    session = make_mock_session()
    session.post.side_effect = requests.RequestException("invalid request")
    provider = IndexNowProvider(api_key="abcdefgh", session=session)

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/article")

    assert captured.value.retryable is False


def test_indexnow_provider_creates_session_by_default() -> None:
    with patch("kliz._http.requests.Session") as session_factory:
        IndexNowProvider(api_key="abcdefgh")

    session_factory.assert_called_once_with()


def test_indexnow_provider_close_releases_session() -> None:
    session = make_mock_session()
    provider = IndexNowProvider(api_key="abcdefgh", session=session)

    provider.close()

    session.close.assert_called_once_with()


@pytest.mark.parametrize(
    "api_key",
    ["", "short", "contains_underscore", "a" * 129],
)
def test_indexnow_provider_rejects_invalid_keys(api_key: str) -> None:
    with pytest.raises(ValueError, match="api_key"):
        IndexNowProvider(api_key=api_key)


def test_indexnow_provider_rejects_invalid_timeout() -> None:
    with pytest.raises(ValueError, match="timeout"):
        IndexNowProvider(api_key="abcdefgh", timeout=0)


@pytest.mark.parametrize(
    "url",
    ["", "ftp://example.com/page", "https:///missing-host", "https://u:p@x.com"],
)
def test_indexnow_provider_rejects_invalid_urls(url: str) -> None:
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ValueError):
        provider.notify(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/article?utm_source=newsletter",
        "https://example.com/article#section",
    ],
)
def test_indexnow_provider_requires_clean_urls(url: str) -> None:
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ValueError, match="query|fragment"):
        provider.notify(url)


def test_indexnow_provider_requires_clean_urls_in_batches() -> None:
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ValueError, match="query"):
        provider.notify_many(
            ["https://example.com/clean", "https://example.com/article?x=1"]
        )


@pytest.mark.parametrize(
    "key_location",
    [
        "https://example.com/indexnow-key.txt?token=abc",
        "https://example.com/indexnow-key.txt#section",
    ],
)
def test_indexnow_provider_rejects_dirty_key_locations(key_location: str) -> None:
    with pytest.raises(ValueError):
        IndexNowProvider(api_key="abcdefgh", key_location=key_location)


def test_indexnow_provider_requires_same_host_for_batches() -> None:
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ValueError, match="same host"):
        provider.notify_many(["https://one.example/a", "https://two.example/b"])


def test_indexnow_provider_error_messages_use_provider_name() -> None:
    session = make_mock_session()
    session.post.return_value.status_code = 500
    provider = IndexNowProvider(api_key="abcdefgh", session=session)

    with pytest.raises(ProviderError, match="IndexNowProvider") as captured:
        provider.notify("https://example.com/article")

    assert captured.value.retryable is True


@pytest.mark.parametrize("urls", [[], ["https://example.com"] * 10_001])
def test_indexnow_provider_validates_batch_size(urls: list[str]) -> None:
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ValueError):
        provider.notify_many(urls)


def test_indexnow_provider_rejects_string_as_url_sequence() -> None:
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ValueError, match="sequence"):
        provider.notify_many("https://example.com")  # type: ignore[arg-type]


def test_indexnow_provider_validates_key_location_host() -> None:
    provider = IndexNowProvider(
        api_key="abcdefgh",
        key_location="https://keys.example/key.txt",
    )

    with pytest.raises(ValueError, match="same host"):
        provider.notify("https://example.com/article")


def test_indexnow_provider_validates_key_location_path() -> None:
    provider = IndexNowProvider(
        api_key="abcdefgh",
        key_location="https://example.com/catalog/key.txt",
    )

    with pytest.raises(ValueError, match="path covered"):
        provider.notify("https://example.com/help/article")


def test_indexnow_provider_rejects_invalid_key_location() -> None:
    with pytest.raises(ValueError):
        IndexNowProvider(api_key="abcdefgh", key_location="not-a-url")


def test_google_provider_builds_client_lazily_on_first_notify(
    google_client_mocks: dict[str, Mock],
) -> None:
    credentials = google_client_mocks["credentials_factory"].return_value
    raw_http = google_client_mocks["http_factory"].return_value
    authorized_http = google_client_mocks["authorized_http_factory"].return_value

    provider = GoogleProvider(
        "/secrets/google-service-account.json",
        timeout=15,
        num_retries=3,
    )

    google_client_mocks["credentials_factory"].assert_not_called()
    google_client_mocks["build"].assert_not_called()

    assert provider.notify("https://example.com/jobs/backend-python") is True
    assert provider.notify("https://example.com/jobs/frontend-python") is True

    google_client_mocks["credentials_factory"].assert_called_once_with(
        "/secrets/google-service-account.json",
        scopes=["https://www.googleapis.com/auth/indexing"],
    )
    google_client_mocks["http_factory"].assert_called_once_with(timeout=15)
    google_client_mocks["authorized_http_factory"].assert_called_once_with(
        credentials,
        http=raw_http,
    )
    google_client_mocks["build"].assert_called_once_with(
        "indexing",
        "v3",
        http=authorized_http,
        cache_discovery=False,
    )
    assert provider.num_retries == 3


def test_google_provider_wraps_configuration_errors(
    google_client_mocks: dict[str, Mock],
) -> None:
    google_client_mocks["credentials_factory"].side_effect = FileNotFoundError(
        "no such file"
    )
    provider = GoogleProvider("/secrets/missing.json")

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/job")

    assert captured.value.retryable is False
    assert captured.value.provider == "GoogleProvider"

    google_client_mocks["credentials_factory"].side_effect = None
    assert provider.notify("https://example.com/job") is True


def test_google_provider_publishes_url_updated(
    google_client_mocks: dict[str, Mock],
) -> None:
    service = google_client_mocks["build"].return_value
    publish_request = service.urlNotifications.return_value.publish.return_value
    provider = GoogleProvider("/secrets/google-service-account.json")

    assert provider.notify(" https://example.com/articles/updated ") is True

    service.urlNotifications.return_value.publish.assert_called_once_with(
        body={
            "url": "https://example.com/articles/updated",
            "type": "URL_UPDATED",
        }
    )
    publish_request.execute.assert_called_once_with(num_retries=2)


@pytest.mark.parametrize(
    ("status_code", "retryable"),
    [(400, False), (403, False), (429, True), (500, True)],
)
def test_google_provider_classifies_api_errors(
    google_client_mocks: dict[str, Mock],
    status_code: int,
    retryable: bool,
) -> None:
    response = Mock(status=status_code, reason="failure")
    error = HttpError(response, b'{"error": {"message": "failure"}}')
    service = google_client_mocks["build"].return_value
    service.urlNotifications.return_value.publish.return_value.execute.side_effect = (
        error
    )
    provider = GoogleProvider("/secrets/google-service-account.json")

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/job")

    assert captured.value.status_code == status_code
    assert captured.value.retryable is retryable
    assert captured.value.provider == "GoogleProvider"


@pytest.mark.parametrize(
    "exception",
    [
        TransportError("transport"),
        httplib2.ServerNotFoundError("offline"),
        OSError("socket"),
    ],
)
def test_google_provider_wraps_transport_errors(
    google_client_mocks: dict[str, Mock],
    exception: Exception,
) -> None:
    service = google_client_mocks["build"].return_value
    service.urlNotifications.return_value.publish.return_value.execute.side_effect = (
        exception
    )
    provider = GoogleProvider("/secrets/google-service-account.json")

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/job")

    assert captured.value.retryable is True


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"service_account_file": ""}, "service_account_file"),
        ({"service_account_file": "account.json", "timeout": 0}, "timeout"),
        ({"service_account_file": "account.json", "num_retries": -1}, "num_retries"),
    ],
)
def test_google_provider_validates_configuration(
    google_client_mocks: dict[str, Mock],
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        GoogleProvider(**kwargs)  # type: ignore[arg-type]


def test_google_provider_rejects_invalid_url(
    google_client_mocks: dict[str, Mock],
) -> None:
    provider = GoogleProvider("/secrets/google-service-account.json")

    with pytest.raises(ValueError):
        provider.notify("not-a-url")


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/job?id=123",
        "https://example.com/job#apply",
    ],
)
def test_google_provider_requires_clean_urls(
    google_client_mocks: dict[str, Mock],
    url: str,
) -> None:
    provider = GoogleProvider("/secrets/google-service-account.json")

    with pytest.raises(ValueError, match="query|fragment"):
        provider.notify(url)


def _verifying_provider(
    *,
    status_code: int = 200,
    text: str = "indexnow-key",
    headers: Optional[dict[str, str]] = None,
    key_location: Optional[str] = None,
) -> tuple[IndexNowProvider, Mock]:
    session = make_mock_session()
    session.get.return_value = Mock(
        status_code=status_code,
        text=text,
        headers=headers if headers is not None else {"Content-Type": "text/plain"},
    )
    provider = IndexNowProvider(
        api_key="indexnow-key", key_location=key_location, session=session
    )
    return provider, session


def test_indexnow_generate_key_is_valid_and_random() -> None:
    key = IndexNowProvider.generate_key()

    assert len(key) == 32
    assert key.isalnum()
    assert IndexNowProvider(api_key=key).api_key == key
    assert IndexNowProvider.generate_key() != key
    assert len(IndexNowProvider.generate_key(8)) == 8


@pytest.mark.parametrize("length", [7, 129, 0])
def test_indexnow_generate_key_rejects_out_of_range_lengths(length: int) -> None:
    with pytest.raises(ValueError, match="between 8 and 128"):
        IndexNowProvider.generate_key(length)


@pytest.mark.parametrize("length", [True, 32.0, "32"])
def test_indexnow_generate_key_rejects_non_integer_lengths(length: object) -> None:
    with pytest.raises(TypeError):
        IndexNowProvider.generate_key(length)  # type: ignore[arg-type]


def test_indexnow_key_file_url_defaults_to_site_root() -> None:
    provider = IndexNowProvider(api_key="indexnow-key")

    assert (
        provider.key_file_url("HTTPS://example.com:8443/some/page")
        == "https://example.com:8443/indexnow-key.txt"
    )
    with pytest.raises(ValueError, match="site_url is required"):
        provider.key_file_url()


def test_indexnow_key_file_url_prefers_key_location() -> None:
    provider = IndexNowProvider(
        api_key="indexnow-key", key_location="https://example.com/k/key.txt"
    )

    assert provider.key_file_url("https://other.example") == (
        "https://example.com/k/key.txt"
    )


def test_indexnow_verify_key_accepts_matching_file() -> None:
    provider, session = _verifying_provider(text="indexnow-key\n")

    assert provider.verify_key("https://example.com") == (
        "https://example.com/indexnow-key.txt"
    )
    session.get.assert_called_once_with(
        "https://example.com/indexnow-key.txt",
        timeout=10.0,
        allow_redirects=False,
    )


def test_indexnow_verify_key_detects_html_soft_404() -> None:
    provider, _ = _verifying_provider(
        text="<!DOCTYPE html><html>...</html>",
        headers={"Content-Type": "text/html; charset=utf-8"},
    )

    with pytest.raises(ProviderError, match="HTML page") as excinfo:
        provider.verify_key("https://example.com")
    assert excinfo.value.retryable is False


def test_indexnow_verify_key_detects_wrong_content() -> None:
    provider, _ = _verifying_provider(text="another-key")

    with pytest.raises(ProviderError, match="does not contain the API key"):
        provider.verify_key("https://example.com")


def test_indexnow_verify_key_rejects_redirects() -> None:
    provider, _ = _verifying_provider(
        status_code=308,
        text="",
        headers={"Location": "https://www.example.com/indexnow-key.txt"},
    )

    with pytest.raises(ProviderError, match=r"redirects \(HTTP 308\) to https://www"):
        provider.verify_key("https://example.com")


@pytest.mark.parametrize(
    ("status_code", "retryable"), [(404, False), (429, True), (503, True)]
)
def test_indexnow_verify_key_reports_http_errors(
    status_code: int, retryable: bool
) -> None:
    provider, _ = _verifying_provider(status_code=status_code, text="")

    with pytest.raises(ProviderError, match=f"HTTP {status_code}") as excinfo:
        provider.verify_key("https://example.com")
    assert excinfo.value.retryable is retryable
    assert excinfo.value.status_code == status_code


def test_indexnow_verify_key_wraps_network_errors() -> None:
    provider, session = _verifying_provider()
    session.get.side_effect = requests.ConnectionError("down")

    with pytest.raises(ProviderError, match="could not be reached") as excinfo:
        provider.verify_key("https://example.com")
    assert excinfo.value.retryable is True


def test_search_console_builds_client_lazily_with_webmasters_scope(
    google_client_mocks: dict[str, Mock],
) -> None:
    provider = GoogleSearchConsoleProvider("/secrets/sa.json", "https://a.example")

    google_client_mocks["build"].assert_not_called()
    assert provider.notify("https://a.example/page") is True
    assert provider.notify("https://a.example/other") is True

    google_client_mocks["credentials_factory"].assert_called_once_with(
        "/secrets/sa.json",
        scopes=["https://www.googleapis.com/auth/webmasters"],
    )
    google_client_mocks["build"].assert_called_once_with(
        "searchconsole",
        "v1",
        http=google_client_mocks["authorized_http_factory"].return_value,
        cache_discovery=False,
    )


def test_search_console_resubmits_the_sitemap(
    google_client_mocks: dict[str, Mock],
) -> None:
    sitemaps = google_client_mocks["build"].return_value.sitemaps.return_value
    provider = GoogleSearchConsoleProvider(
        "/secrets/sa.json", "https://a.example/", num_retries=4
    )

    assert provider.notify_many(["https://a.example/1", "https://a.example/2"])

    sitemaps.submit.assert_called_once_with(
        siteUrl="https://a.example/", feedpath="https://a.example/sitemap.xml"
    )
    sitemaps.submit.return_value.execute.assert_called_once_with(num_retries=4)


@pytest.mark.parametrize(
    ("site_url", "sitemap_url", "expected_site", "expected_sitemap"),
    [
        (
            "HTTPS://A.example",
            None,
            "https://a.example/",
            "https://a.example/sitemap.xml",
        ),
        (
            "https://a.example/blog",
            None,
            "https://a.example/blog/",
            "https://a.example/blog/sitemap.xml",
        ),
        (
            " SC-Domain:A.Example. ",
            None,
            "sc-domain:a.example",
            "https://a.example/sitemap.xml",
        ),
        (
            "sc-domain:a.example",
            "https://www.a.example/sitemap_index.xml",
            "sc-domain:a.example",
            "https://www.a.example/sitemap_index.xml",
        ),
    ],
)
def test_search_console_normalizes_property_and_default_sitemap(
    site_url: str,
    sitemap_url: Optional[str],
    expected_site: str,
    expected_sitemap: str,
) -> None:
    provider = GoogleSearchConsoleProvider("sa.json", site_url, sitemap_url)

    assert provider.site_url == expected_site
    assert provider.sitemap_url == expected_sitemap


@pytest.mark.parametrize(
    ("site_url", "inside", "outside"),
    [
        (
            "https://a.example/blog/",
            ["https://a.example/blog/", "https://A.example/blog/post?id=1"],
            [
                "http://a.example/blog/x",
                "https://a.example/shop",
                "https://www.a.example/blog/x",
                "https://a.example:8443/blog/x",
            ],
        ),
        (
            "sc-domain:a.example",
            ["http://a.example/x", "https://www.a.example/y"],
            ["https://b.example/", "https://evila.example/"],
        ),
    ],
)
def test_search_console_validates_urls_against_the_property(
    site_url: str, inside: list[str], outside: list[str]
) -> None:
    provider = GoogleSearchConsoleProvider(
        "sa.json", site_url, "https://a.example/blog/sitemap.xml"
    )

    for url in inside:
        assert provider.validate_url(url).hostname
    for url in outside:
        with pytest.raises(ValueError, match="outside the Search Console property"):
            provider.validate_url(url)


def test_search_console_does_not_submit_when_a_url_is_outside(
    google_client_mocks: dict[str, Mock],
) -> None:
    provider = GoogleSearchConsoleProvider("sa.json", "https://a.example/")

    with pytest.raises(ValueError, match="outside"):
        provider.notify_many(["https://a.example/1", "https://b.example/2"])
    with pytest.raises(ValueError, match="non-empty"):
        provider.notify_many([])
    google_client_mocks["build"].assert_not_called()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"site_url": ""}, "site_url"),
        ({"site_url": "sc-domain:"}, "sc-domain:example.com"),
        ({"site_url": "sc-domain:a.example/path"}, "sc-domain:example.com"),
        ({"site_url": "ftp://a.example"}, "http"),
        ({"site_url": "https://a.example/?x=1"}, "query"),
        (
            {
                "site_url": "https://a.example/",
                "sitemap_url": "https://b.example/s.xml",
            },
            "sitemap_url is invalid",
        ),
        ({"site_url": "https://a.example/", "timeout": 0}, "timeout"),
    ],
)
def test_search_console_validates_configuration(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        GoogleSearchConsoleProvider("sa.json", **kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("status_code", "retryable", "hint"),
    [
        (403, False, "Owner or Full user"),
        (404, False, "exact form"),
        (400, False, "HTTP 400"),
        (503, True, "HTTP 503"),
    ],
)
def test_search_console_explains_api_errors(
    google_client_mocks: dict[str, Mock],
    status_code: int,
    retryable: bool,
    hint: str,
) -> None:
    error = HttpError(Mock(status=status_code, reason="x"), b"{}")
    sitemaps = google_client_mocks["build"].return_value.sitemaps.return_value
    sitemaps.submit.return_value.execute.side_effect = error
    provider = GoogleSearchConsoleProvider("sa.json", "https://a.example/")

    with pytest.raises(ProviderError, match=hint) as captured:
        provider.notify("https://a.example/")

    assert captured.value.retryable is retryable
    assert captured.value.status_code == status_code
    assert captured.value.provider == "GoogleSearchConsoleProvider"


def test_kliz_rejects_outside_urls_individually_for_search_console(
    google_client_mocks: dict[str, Mock],
) -> None:
    sitemaps = google_client_mocks["build"].return_value.sitemaps.return_value
    indexer = Kliz([GoogleSearchConsoleProvider("sa.json", "https://a.example/")])

    results = indexer.notify_many_detailed(
        ["https://a.example/1", "https://b.example/2", "https://a.example/3"]
    )["GoogleSearchConsoleProvider"]

    assert [(r.success, r.urls) for r in results] == [
        (False, ("https://b.example/2",)),
        (True, ("https://a.example/1", "https://a.example/3")),
    ]
    sitemaps.submit.assert_called_once()
