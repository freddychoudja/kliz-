"""Tests for BatchProvider scaffolding."""

from urllib.parse import SplitResult

import pytest

from kliz import BatchProvider


class TinyBatchProvider(BatchProvider):
    max_urls_per_request = 2

    def __init__(self) -> None:
        super().__init__(timeout=1.0)
        self.batches: list[list[str]] = []

    def _notify_many(self, urls: list[str], parsed_urls: list[SplitResult]) -> bool:
        del parsed_urls
        self.batches.append(list(urls))
        return True


def test_batch_provider_gives_notify_many_for_free() -> None:
    provider = TinyBatchProvider()

    assert provider.notify("https://example.com/only") is True
    assert provider.batches == [["https://example.com/only"]]
    assert provider.notify_many(["https://example.com/one", "https://example.com/two"])
    assert provider.batches[-1] == [
        "https://example.com/one",
        "https://example.com/two",
    ]


def test_batch_provider_enforces_same_host_and_limits() -> None:
    provider = TinyBatchProvider()

    with pytest.raises(ValueError, match="same host"):
        provider.notify_many(["https://a.example/x", "https://b.example/y"])
    with pytest.raises(ValueError, match="at most 2"):
        provider.notify_many(
            [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ]
        )
