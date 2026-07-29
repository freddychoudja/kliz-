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
