"""Provider orchestration for kliz."""

from __future__ import annotations

import random
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from typing import Any
from urllib.parse import SplitResult

from kliz.exceptions import ProviderError
from kliz.providers.base import BaseProvider
from kliz.results import NotificationResult

_RETRY_BASE_DELAY = 1.0
_JITTER_RATIO = 0.25


class Kliz:
    """Dispatch indexing notifications to a collection of providers.

    Retry is off by default (``max_attempts=1``). When enabled, retryable
    failures wait for the server's ``Retry-After`` if it sent one, otherwise
    for an exponential backoff (1 s, 2 s, 4 s... plus up to 25 % jitter)
    capped at ``max_delay``. A ``Retry-After`` longer than ``max_delay``, or a
    wait that would overrun ``deadline`` (seconds since the first attempt),
    stops retrying; the result then carries ``retry_after`` so the caller can
    schedule a later attempt.
    """

    def __init__(
        self,
        providers: Iterable[BaseProvider],
        *,
        max_attempts: int = 1,
        max_delay: float = 60.0,
        deadline: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
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
        if not max_delay > 0:
            raise ValueError("max_delay must be greater than zero")
        if deadline is not None and not deadline > 0:
            raise ValueError("deadline must be greater than zero")

        self.providers = tuple(provider_list)
        self.max_attempts = max_attempts
        self.max_delay = max_delay
        self.deadline = deadline
        self._sleep = sleep
        self._clock = clock
        self._rng = rng if rng is not None else random.Random()

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
            for provider, name in zip(self.providers, self._result_names(), strict=True)
        }

    def notify_many(self, urls: Sequence[str]) -> dict[str, bool]:
        """Notify every provider with a batch of URLs and return boolean statuses."""

        return {
            name: all(result.success for result in results)
            for name, results in self.notify_many_detailed(urls).items()
        }

    def notify_many_detailed(
        self, urls: Sequence[str]
    ) -> dict[str, list[NotificationResult]]:
        """Notify all providers with multiple URLs.

        URLs are stripped and deduplicated. For batch providers exposing
        ``validate_url``, invalid URLs are reported as individual failures
        (listed first) and valid ones are grouped by host before chunking, so
        one bad or foreign URL never sinks a whole batch. Each result's
        ``urls`` tells which URLs it covers.
        """

        url_list = self._validate_urls(urls)
        return {
            name: self._notify_provider_many(provider, url_list)
            for provider, name in zip(self.providers, self._result_names(), strict=True)
        }

    def _notify_provider(self, provider: BaseProvider, url: str) -> NotificationResult:
        return self._execute_with_retry(provider, provider.notify, url, (url,))

    def _notify_provider_many(
        self, provider: BaseProvider, urls: list[str]
    ) -> list[NotificationResult]:
        notify_many_fn = getattr(provider, "notify_many", None)
        if not callable(notify_many_fn):
            return [
                self._execute_with_retry(provider, provider.notify, url, (url,))
                for url in urls
            ]

        rejected: list[NotificationResult] = []
        batches = [urls]
        validate_url = getattr(provider, "validate_url", None)
        if callable(validate_url):
            rejected, batches = self._group_by_host(provider, validate_url, urls)

        max_urls = getattr(provider, "max_urls_per_request", None)
        if isinstance(max_urls, int) and max_urls > 0:
            chunks = [
                batch[i : i + max_urls]
                for batch in batches
                for i in range(0, len(batch), max_urls)
            ]
        else:
            chunks = batches

        return rejected + [
            self._execute_with_retry(provider, notify_many_fn, chunk, tuple(chunk))
            for chunk in chunks
        ]

    @staticmethod
    def _group_by_host(
        provider: BaseProvider,
        validate_url: Callable[[str], SplitResult],
        urls: list[str],
    ) -> tuple[list[NotificationResult], list[list[str]]]:
        rejected: list[NotificationResult] = []
        groups: dict[str, list[str]] = {}
        for url in urls:
            try:
                parsed_url = validate_url(url)
            except ValueError as exc:
                rejected.append(
                    NotificationResult(
                        provider=provider.name,
                        success=False,
                        error=str(exc),
                        urls=(url,),
                    )
                )
                continue
            host = (parsed_url.hostname or "").lower()
            groups.setdefault(host, []).append(url)
        return rejected, list(groups.values())

    def _execute_with_retry(
        self,
        provider: BaseProvider,
        func: Callable[[Any], Any],
        payload: Any,
        urls: tuple[str, ...],
    ) -> NotificationResult:
        started = self._clock()
        for attempt in range(1, self.max_attempts + 1):
            try:
                success = bool(func(payload))
                return NotificationResult(
                    provider=provider.name,
                    success=success,
                    error=None if success else "provider returned False",
                    urls=urls,
                    attempts=attempt,
                )
            except ProviderError as exc:
                delay = self._retry_delay(attempt, exc, started)
                if delay is not None:
                    self._sleep(delay)
                    continue
                return NotificationResult(
                    provider=provider.name,
                    success=False,
                    retryable=exc.retryable,
                    error=str(exc),
                    status_code=exc.status_code,
                    urls=urls,
                    retry_after=exc.retry_after,
                    attempts=attempt,
                )
            except Exception as exc:
                return NotificationResult(
                    provider=provider.name,
                    success=False,
                    error=str(exc) or exc.__class__.__name__,
                    urls=urls,
                    attempts=attempt,
                )
        raise AssertionError("unreachable")  # pragma: no cover

    def _validate_urls(self, urls: Sequence[str]) -> list[str]:
        if isinstance(urls, (str, bytes)):
            raise TypeError("urls must be a sequence of strings, not a string or bytes")
        try:
            url_list = list(urls)
        except TypeError as exc:
            raise TypeError("urls must be an iterable sequence of strings") from exc

        if not url_list:
            raise ValueError("urls must be a non-empty sequence")
        if not all(isinstance(url, str) for url in url_list):
            raise TypeError("urls must be a sequence of strings")
        return list(dict.fromkeys(url.strip() for url in url_list))

    def _retry_delay(
        self, attempt: int, exc: ProviderError, started: float
    ) -> float | None:
        """Return how long to wait before the next attempt, or ``None`` to stop."""

        if not exc.retryable or attempt >= self.max_attempts:
            return None
        if exc.retry_after is not None:
            if exc.retry_after > self.max_delay:
                return None
            delay = exc.retry_after
        else:
            backoff = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
            jitter = 1.0 + self._rng.uniform(0.0, _JITTER_RATIO)
            delay = min(backoff * jitter, self.max_delay)
        if self.deadline is not None:
            if self._clock() - started + delay > self.deadline:
                return None
        return delay

    def _result_names(self) -> list[str]:
        counts: Counter[str] = Counter()
        names: list[str] = []
        for provider in self.providers:
            counts[provider.name] += 1
            occurrence = counts[provider.name]
            suffix = "" if occurrence == 1 else f"#{occurrence}"
            names.append(f"{provider.name}{suffix}")
        return names
