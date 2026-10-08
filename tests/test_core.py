"""Tests for provider orchestration."""

from typing import Optional
from unittest.mock import Mock

import pytest
from conftest import (
    BatchStubProvider,
    CountingProvider,
    FlakyProvider,
    NamedProvider,
    RecordingSleep,
    StubProvider,
    make_mock_session,
    raise_non_retryable,
    raise_retryable,
    raise_unknown,
    return_false,
    return_true,
)

from kliz import IndexNowProvider, Kliz, NotificationResult


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
        urls=("https://example.com",),
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


def test_provider_iterables_are_copied_to_an_immutable_tuple() -> None:
    provider = StubProvider(return_true)
    indexer = Kliz(provider for provider in [provider])

    assert indexer.providers == (provider,)


@pytest.mark.parametrize("providers", ["invalid", [object()]])
def test_invalid_provider_collections_are_rejected(providers: object) -> None:
    with pytest.raises(TypeError):
        Kliz(providers)  # type: ignore[arg-type]


def test_retry_is_disabled_by_default() -> None:
    sleeper = RecordingSleep()
    provider = CountingProvider(raise_retryable)
    indexer = Kliz([provider], sleep=sleeper, clock=lambda: 0.0)

    result = indexer.notify_all_detailed("https://example.com")["CountingProvider"]

    assert result.retryable is True
    assert provider.calls == 1
    assert sleeper.delays == []


def test_retry_succeeds_on_second_attempt_with_exponential_backoff() -> None:
    sleeper = RecordingSleep()
    provider = FlakyProvider(failures=1)
    indexer = Kliz(
        [provider],
        max_attempts=3,
        sleep=sleeper,
        clock=lambda: 0.0,
    )

    result = indexer.notify_all_detailed("https://example.com")["FlakyProvider"]

    assert result == NotificationResult(
        provider="FlakyProvider", success=True, urls=("https://example.com",)
    )
    assert provider.calls == 2
    assert len(sleeper.delays) == 1
    assert 1.0 <= sleeper.delays[0] <= 1.25


def test_retry_stops_after_max_attempts_and_preserves_error() -> None:
    sleeper = RecordingSleep()
    provider = FlakyProvider(failures=10)
    indexer = Kliz(
        [provider],
        max_attempts=3,
        sleep=sleeper,
        clock=lambda: 0.0,
    )

    result = indexer.notify_all_detailed("https://example.com")["FlakyProvider"]

    assert result == NotificationResult(
        provider="FlakyProvider",
        success=False,
        retryable=True,
        error="temporary failure",
        status_code=429,
        urls=("https://example.com",),
    )
    assert provider.calls == 3
    assert len(sleeper.delays) == 2
    assert 1.0 <= sleeper.delays[0] <= 1.25
    assert 2.0 <= sleeper.delays[1] <= 2.25


def test_non_retryable_errors_are_not_repeated() -> None:
    sleeper = RecordingSleep()
    provider = CountingProvider(raise_non_retryable)
    indexer = Kliz(
        [provider],
        max_attempts=3,
        sleep=sleeper,
        clock=lambda: 0.0,
    )

    result = indexer.notify_all_detailed("https://example.com")["CountingProvider"]

    assert result == NotificationResult(
        provider="CountingProvider",
        success=False,
        retryable=False,
        error="permanent failure",
        status_code=400,
        urls=("https://example.com",),
    )
    assert provider.calls == 1
    assert sleeper.delays == []


def test_false_return_is_not_retried() -> None:
    sleeper = RecordingSleep()
    provider = CountingProvider(return_false)
    indexer = Kliz(
        [provider],
        max_attempts=3,
        sleep=sleeper,
        clock=lambda: 0.0,
    )

    result = indexer.notify_all_detailed("https://example.com")["CountingProvider"]

    assert result.success is False
    assert result.retryable is False
    assert result.error == "provider returned False"
    assert provider.calls == 1
    assert sleeper.delays == []


def test_unknown_errors_are_not_retried() -> None:
    sleeper = RecordingSleep()
    provider = CountingProvider(raise_unknown)
    indexer = Kliz(
        [provider],
        max_attempts=3,
        sleep=sleeper,
        clock=lambda: 0.0,
    )

    result = indexer.notify_all_detailed("https://example.com")["CountingProvider"]

    assert result.success is False
    assert result.retryable is False
    assert result.error == "unexpected failure"
    assert provider.calls == 1
    assert sleeper.delays == []


@pytest.mark.parametrize("max_attempts", [0, -1, 1.5, "two", True])
def test_invalid_max_attempts_are_rejected(max_attempts: object) -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        Kliz(
            [StubProvider(return_true)],
            max_attempts=max_attempts,  # type: ignore[arg-type]
        )


def test_close_calls_close_on_every_provider() -> None:
    providers = [StubProvider(return_true), StubProvider(return_true)]
    closed: list[str] = []
    for i, p in enumerate(providers):
        p.close = lambda _i=i: closed.append(f"p{_i}")  # type: ignore[assignment]
    indexer = Kliz(providers)

    indexer.close()

    assert closed == ["p0", "p1"]


def test_context_manager_calls_close_on_exit() -> None:
    provider = StubProvider(return_true)
    closed: list[bool] = []
    provider.close = lambda: closed.append(True)  # type: ignore[assignment]

    with Kliz([provider]) as indexer:
        indexer.notify_all("https://example.com")

    assert closed == [True]


def test_base_provider_close_is_a_noop() -> None:
    provider = StubProvider(return_true)
    # Should not raise — BaseProvider.close() is a no-op by default.
    provider.close()


def test_notify_many_returns_boolean_statuses() -> None:
    batch_provider = BatchStubProvider(lambda urls: True)
    single_provider = StubProvider(return_true)
    indexer = Kliz([batch_provider, single_provider])

    statuses = indexer.notify_many(["https://example.com/1", "https://example.com/2"])

    assert statuses == {
        "BatchStubProvider": True,
        "StubProvider": True,
    }


def test_notify_many_delegates_to_batch_provider() -> None:
    provider = BatchStubProvider()
    indexer = Kliz([provider])
    urls = ["https://example.com/1", "https://example.com/2"]

    indexer.notify_many(urls)

    assert provider.batches == [urls]


def test_notify_many_detailed_falls_back_to_notify_loop() -> None:
    provider = CountingProvider(return_true)
    indexer = Kliz([provider])
    urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]

    results = indexer.notify_many_detailed(urls)

    assert provider.calls == 3
    assert len(results["CountingProvider"]) == 3
    assert all(r.success for r in results["CountingProvider"])


def test_notify_many_respects_max_urls_per_request() -> None:
    provider = BatchStubProvider(max_urls_per_request=2)
    indexer = Kliz([provider])
    urls = [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
        "https://example.com/4",
        "https://example.com/5",
    ]

    results = indexer.notify_many_detailed(urls)

    assert provider.batches == [
        ["https://example.com/1", "https://example.com/2"],
        ["https://example.com/3", "https://example.com/4"],
        ["https://example.com/5"],
    ]
    assert len(results["BatchStubProvider"]) == 3
    assert all(r.success for r in results["BatchStubProvider"])


@pytest.mark.parametrize(
    "invalid_urls",
    ["https://example.com", b"https://example.com", [], None, 123],
)
def test_notify_many_validates_urls_sequence(invalid_urls: object) -> None:
    indexer = Kliz([StubProvider(return_true)])

    with pytest.raises((TypeError, ValueError)):
        indexer.notify_many(invalid_urls)  # type: ignore[arg-type]


def test_notify_many_retries_transient_failure() -> None:
    sleeper = RecordingSleep()
    calls = 0

    def flaky_batch(urls: object) -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise_retryable("https://example.com")
        return True

    provider = BatchStubProvider(flaky_batch)
    indexer = Kliz([provider], max_attempts=3, sleep=sleeper, clock=lambda: 0.0)

    results = indexer.notify_many_detailed(["https://example.com/1"])

    assert calls == 2
    assert len(sleeper.delays) == 1
    assert results["BatchStubProvider"][0].success is True


def test_notify_many_continues_across_providers() -> None:
    failing = StubProvider(return_false)
    succeeding = BatchStubProvider()
    indexer = Kliz([failing, succeeding])

    statuses = indexer.notify_many(["https://example.com/1"])

    assert statuses == {
        "StubProvider": False,
        "BatchStubProvider": True,
    }


def _indexnow_with_session(
    key_location: Optional[str] = None,
) -> tuple[IndexNowProvider, Mock]:
    session = make_mock_session()
    session.post.return_value = Mock(status_code=200)
    provider = IndexNowProvider(
        api_key="abcdefgh12", key_location=key_location, session=session
    )
    return provider, session


def test_notify_many_groups_mixed_hosts_into_separate_batches() -> None:
    provider, session = _indexnow_with_session()
    indexer = Kliz([provider])

    results = indexer.notify_many_detailed(
        [
            "https://a.example/1",
            "https://www.a.example/2",
            "https://a.example/3",
        ]
    )["IndexNowProvider"]

    assert [r.success for r in results] == [True, True]
    assert [r.urls for r in results] == [
        ("https://a.example/1", "https://a.example/3"),
        ("https://www.a.example/2",),
    ]
    hosts = [call.kwargs["json"]["host"] for call in session.post.call_args_list]
    assert hosts == ["a.example", "www.a.example"]


def test_notify_many_rejects_invalid_urls_individually() -> None:
    provider, session = _indexnow_with_session()
    indexer = Kliz([provider])

    results = indexer.notify_many_detailed(
        [
            "https://a.example/1",
            "https://a.example/2?id=1",
            "ftp://a.example/3",
            "https://a.example/4",
        ]
    )["IndexNowProvider"]

    assert results[0] == NotificationResult(
        provider="IndexNowProvider",
        success=False,
        error="url must not contain a query string",
        urls=("https://a.example/2?id=1",),
    )
    assert results[1].success is False
    assert results[1].urls == ("ftp://a.example/3",)
    assert results[2] == NotificationResult(
        provider="IndexNowProvider",
        success=True,
        urls=("https://a.example/1", "https://a.example/4"),
    )
    session.post.assert_called_once()
    assert session.post.call_args.kwargs["json"]["urlList"] == [
        "https://a.example/1",
        "https://a.example/4",
    ]


def test_notify_many_rejects_urls_outside_key_location_individually() -> None:
    provider, session = _indexnow_with_session(
        key_location="https://a.example/blog/key.txt"
    )
    indexer = Kliz([provider])

    results = indexer.notify_many_detailed(
        ["https://a.example/blog/1", "https://a.example/shop/2"]
    )["IndexNowProvider"]

    assert results[0].success is False
    assert results[0].urls == ("https://a.example/shop/2",)
    assert "key_location" in str(results[0].error)
    assert results[1].success is True
    assert results[1].urls == ("https://a.example/blog/1",)
    session.post.assert_called_once()


def test_notify_many_reports_all_rejected_without_sending() -> None:
    provider, session = _indexnow_with_session()
    indexer = Kliz([provider])

    statuses = indexer.notify_many(["https://a.example/1?x=1"])

    assert statuses == {"IndexNowProvider": False}
    session.post.assert_not_called()


def test_notify_many_strips_and_deduplicates_urls() -> None:
    provider = BatchStubProvider()
    indexer = Kliz([provider])

    indexer.notify_many(
        [
            "https://example.com/1",
            " https://example.com/1 ",
            "https://example.com/2",
            "https://example.com/1",
        ]
    )

    assert provider.batches == [["https://example.com/1", "https://example.com/2"]]


def test_notify_many_rejects_non_string_items() -> None:
    indexer = Kliz([StubProvider(return_true)])

    with pytest.raises(TypeError, match="sequence of strings"):
        indexer.notify_many(["https://example.com/1", 42])  # type: ignore[list-item]


def test_notify_many_results_list_covered_urls_per_chunk() -> None:
    provider = BatchStubProvider(max_urls_per_request=2)
    single = StubProvider(return_true)
    indexer = Kliz([provider, single])
    urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]

    results = indexer.notify_many_detailed(urls)

    assert [r.urls for r in results["BatchStubProvider"]] == [
        ("https://example.com/1", "https://example.com/2"),
        ("https://example.com/3",),
    ]
    assert [r.urls for r in results["StubProvider"]] == [(url,) for url in urls]
