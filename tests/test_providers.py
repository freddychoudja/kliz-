"""Unit tests for the built-in indexing providers."""

from collections.abc import Iterator
from contextlib import ExitStack
from unittest.mock import Mock, patch

import httplib2
import pytest
import requests
from google.auth.exceptions import TransportError
from googleapiclient.errors import HttpError

from kliz.exceptions import ProviderError
from kliz.providers.google import GoogleProvider
from kliz.providers.indexnow import IndexNowProvider


@pytest.fixture
def google_client_mocks() -> Iterator[dict[str, Mock]]:
    with ExitStack() as stack:
        credentials_factory = stack.enter_context(
            patch(
                "kliz.providers.google.service_account.Credentials."
                "from_service_account_file"
            )
        )
        http_factory = stack.enter_context(patch("kliz.providers.google.httplib2.Http"))
        authorized_http_factory = stack.enter_context(
            patch("kliz.providers.google.google_auth_httplib2.AuthorizedHttp")
        )
        build = stack.enter_context(patch("kliz.providers.google.build"))
        yield {
            "credentials_factory": credentials_factory,
            "http_factory": http_factory,
            "authorized_http_factory": authorized_http_factory,
            "build": build,
        }


@pytest.mark.parametrize("status_code", [200, 202])
@patch("kliz.providers.indexnow.requests.post")
def test_indexnow_provider_accepts_success_statuses(
    mock_post: Mock, status_code: int
) -> None:
    mock_post.return_value.status_code = status_code
    provider = IndexNowProvider(
        api_key="indexnow-key",
        key_location="https://example.com/indexnow-key.txt",
    )

    assert provider.notify("https://example.com/articles/new") is True

    mock_post.assert_called_once_with(
        "https://api.indexnow.org/indexnow",
        json={
            "host": "example.com",
            "key": "indexnow-key",
            "keyLocation": "https://example.com/indexnow-key.txt",
            "urlList": ["https://example.com/articles/new"],
        },
        timeout=10.0,
    )


@patch("kliz.providers.indexnow.requests.post")
def test_indexnow_provider_submits_multiple_urls(mock_post: Mock) -> None:
    mock_post.return_value.status_code = 200
    provider = IndexNowProvider(api_key="abcdefgh")
    urls = [
        "https://example.com/first",
        "https://example.com/second",
    ]

    assert provider.notify_many(urls) is True
    assert mock_post.call_args.kwargs["json"]["urlList"] == urls


@pytest.mark.parametrize(
    ("status_code", "retryable"),
    [(400, False), (403, False), (422, False), (429, True), (500, True)],
)
@patch("kliz.providers.indexnow.requests.post")
def test_indexnow_provider_classifies_http_errors(
    mock_post: Mock,
    status_code: int,
    retryable: bool,
) -> None:
    mock_post.return_value.status_code = status_code
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/article")

    assert captured.value.status_code == status_code
    assert captured.value.retryable is retryable
    assert captured.value.provider == "IndexNowProvider"


@pytest.mark.parametrize(
    "exception",
    [requests.Timeout("timeout"), requests.ConnectionError("offline")],
)
@patch("kliz.providers.indexnow.requests.post")
def test_indexnow_provider_wraps_transient_network_errors(
    mock_post: Mock,
    exception: requests.RequestException,
) -> None:
    mock_post.side_effect = exception
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/article")

    assert captured.value.retryable is True
    assert captured.value.status_code is None


@patch("kliz.providers.indexnow.requests.post")
def test_indexnow_provider_wraps_other_request_errors(mock_post: Mock) -> None:
    mock_post.side_effect = requests.RequestException("invalid request")
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ProviderError) as captured:
        provider.notify("https://example.com/article")

    assert captured.value.retryable is False


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


def test_indexnow_provider_requires_same_host_for_batches() -> None:
    provider = IndexNowProvider(api_key="abcdefgh")

    with pytest.raises(ValueError, match="same host"):
        provider.notify_many(["https://one.example/a", "https://two.example/b"])


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


def test_google_provider_builds_authenticated_client(
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