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
