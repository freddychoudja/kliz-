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
