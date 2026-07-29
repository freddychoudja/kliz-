"""Tests for provider orchestration."""

from typing import Callable

import pytest

from kliz import Kliz, NotificationResult, ProviderError
from kliz.providers.base import BaseProvider


class StubProvider(BaseProvider):
    def __init__(self, callback: Callable[[str], bool]) -> None:
        self.callback = callback

    def notify(self, url: str) -> bool:
        return self.callback(url)


class NamedProvider(StubProvider):
    @property
    def name(self) -> str:
        return "custom"


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


def raise_unknown(url: str) -> bool:
    raise RuntimeError("unexpected failure")


def test_notify_all_returns_boolean_statuses() -> None:
    indexer = Kliz([StubProvider(return_true), NamedProvider(return_false)])

    assert indexer.notify_all("https://example.com") == {
        "StubProvider": True,
        "custom": False,
    }


def test_notify_all_detailed_preserves_retry_information() -> None:
    indexer = Kliz([StubProvider(raise_retryable)])

    result = indexer.notify_all_detailed("https://example.com")["StubProvider"]

    assert result == NotificationResult(
        provider="StubProvider",
        success=False,
        retryable=True,
        error="temporary failure",
        status_code=429,
    )


def test_notify_all_detailed_captures_unknown_exceptions() -> None:
    indexer = Kliz([StubProvider(raise_unknown)])

    result = indexer.notify_all_detailed("https://example.com")["StubProvider"]

    assert result.success is False
    assert result.retryable is False
    assert result.error == "unexpected failure"


def test_duplicate_provider_names_do_not_overwrite_results() -> None:
    indexer = Kliz([StubProvider(return_true), StubProvider(return_false)])

    assert indexer.notify_all("https://example.com") == {
        "StubProvider": True,
        "StubProvider#2": False,
    }
