"""Shared test fixtures and helpers for the kliz test suite."""

from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack
from unittest.mock import Mock, patch

import pytest
import requests

from kliz.exceptions import ProviderError
from kliz.providers.base import BaseProvider

# ---------------------------------------------------------------------------
# Stub providers
# ---------------------------------------------------------------------------


class StubProvider(BaseProvider):
    def __init__(self, callback: Callable[[str], bool]) -> None:
        self.callback = callback

    def notify(self, url: str) -> bool:
        return self.callback(url)


class BatchStubProvider(BaseProvider):
    def __init__(
        self,
        callback: Callable[[Sequence[str]], bool] | None = None,
        *,
        max_urls_per_request: int | None = None,
    ) -> None:
        self.callback = callback or (lambda urls: True)
        self.max_urls_per_request = max_urls_per_request
        self.batches: list[list[str]] = []

    def notify(self, url: str) -> bool:
        return self.notify_many([url])

    def notify_many(self, urls: Sequence[str]) -> bool:
        urls_list = list(urls)
        self.batches.append(urls_list)
        return self.callback(urls_list)


class NamedProvider(StubProvider):
    @property
    def name(self) -> str:
        return "custom"


class CountingProvider(StubProvider):
    def __init__(self, callback: Callable[[str], bool]) -> None:
        super().__init__(callback)
        self.calls = 0

    def notify(self, url: str) -> bool:
        self.calls += 1
        return super().notify(url)


class FlakyProvider(StubProvider):
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def notify(self, url: str) -> bool:
        self.calls += 1
        if self.calls <= self.failures:
            raise ProviderError(
                "temporary failure",
                provider="StubProvider",
                retryable=True,
                status_code=429,
            )
        return True


# ---------------------------------------------------------------------------
# Callback helpers
# ---------------------------------------------------------------------------


def return_true(url: str) -> bool:
    return bool(url)


def return_false(url: str) -> bool:
    return False


def raise_retryable(url: str) -> bool:
    raise ProviderError(
        "temporary failure",
        provider="StubProvider",
        retryable=True,
        status_code=429,
    )


def raise_non_retryable(url: str) -> bool:
    raise ProviderError(
        "permanent failure",
        provider="StubProvider",
        retryable=False,
        status_code=400,
    )


def raise_unknown(url: str) -> bool:
    raise RuntimeError("unexpected failure")


# ---------------------------------------------------------------------------
# Recording sleep
# ---------------------------------------------------------------------------


class RecordingSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, delay: float) -> None:
        self.delays.append(delay)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def make_mock_session() -> Mock:
    return Mock(spec=requests.Session)


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
