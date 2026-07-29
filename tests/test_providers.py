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

