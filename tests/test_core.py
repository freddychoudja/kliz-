"""Tests for provider orchestration."""

import pytest
from conftest import (
    CountingProvider,
    FlakyProvider,
    NamedProvider,
    RecordingSleep,
    StubProvider,
    raise_non_retryable,
    raise_retryable,
    raise_unknown,
    return_false,
    return_true,
)

from kliz import Kliz, NotificationResult


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

    assert result == NotificationResult(provider="FlakyProvider", success=True)
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
