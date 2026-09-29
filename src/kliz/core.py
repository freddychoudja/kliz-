"""Provider orchestration for kliz."""

from __future__ import annotations

import random
import time
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any

from kliz.exceptions import ProviderError
from kliz.providers.base import BaseProvider
from kliz.results import NotificationResult

_RETRY_BASE_DELAY = 1.0
_JITTER_RANGE = 0.25


class Kliz:
    """Dispatch indexing notifications to a collection of providers."""

    def __init__(
        self,
        providers: Iterable[BaseProvider],
        *,
        max_attempts: int = 1,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if isinstance(providers, (str, bytes)):
            raise TypeError("providers must be an iterable of BaseProvider instances")

        provider_list = list(providers)
        if not all(isinstance(provider, BaseProvider) for provider in provider_list):
            raise TypeError("every provider must inherit from BaseProvider")

        if (
            isinstance(max_attempts, bool)
            or not isinstance(max_attempts, int)
            or max_attempts < 1
        ):
            raise ValueError("max_attempts must be a positive integer")

        self.providers = tuple(provider_list)
        self.max_attempts = max_attempts
        self._sleep = sleep
        self._clock = clock

    def close(self) -> None:
        """Close every provider, releasing pooled connections."""

        for provider in self.providers:
            provider.close()

    def __enter__(self) -> Kliz:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def notify_all(self, url: str) -> dict[str, bool]:
        """Notify every provider and return simple boolean statuses."""

        return {
            name: result.success
            for name, result in self.notify_all_detailed(url).items()
        }

    def notify_all_detailed(self, url: str) -> dict[str, NotificationResult]:
        """Notify all providers without hiding error and retry information."""

        return {
            name: self._notify_provider(provider, url)
            for provider, name in zip(self.providers, self._result_names())
        }

    def _notify_provider(self, provider: BaseProvider, url: str) -> NotificationResult:
        for attempt in range(1, self.max_attempts + 1):
            try:
                success = bool(provider.notify(url))
                return NotificationResult(
                    provider=provider.name,
                    success=success,
                    error=None if success else "provider returned False",
                )
            except ProviderError as exc:
                if attempt < self.max_attempts and exc.retryable:
                    self._sleep_between_attempts(attempt)
                    continue
                return NotificationResult(
                    provider=provider.name,
                    success=False,
                    retryable=exc.retryable,
                    error=str(exc),
                    status_code=exc.status_code,
                )
            except Exception as exc:
                return NotificationResult(
                    provider=provider.name,
                    success=False,
                    error=str(exc) or exc.__class__.__name__,
                )
        raise AssertionError("unreachable")

    def _sleep_between_attempts(self, attempt: int) -> None:
        delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
        delay += random.Random(self._clock()).uniform(0.0, _JITTER_RANGE)
        self._sleep(delay)

    def _result_names(self) -> list[str]:
        counts: Counter[str] = Counter()
        names: list[str] = []
        for provider in self.providers:
            counts[provider.name] += 1
            occurrence = counts[provider.name]
            suffix = "" if occurrence == 1 else f"#{occurrence}"
            names.append(f"{provider.name}{suffix}")
        return names
