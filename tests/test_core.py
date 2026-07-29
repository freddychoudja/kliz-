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

