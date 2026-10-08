"""Result models returned by the kliz orchestrator."""

from dataclasses import dataclass

from kliz.exceptions import ProviderError


@dataclass(frozen=True)
class NotificationResult:
    """Detailed outcome of one provider notification."""

    provider: str
    success: bool
    retryable: bool = False
    error: str | None = None
    status_code: int | None = None
    urls: tuple[str, ...] = ()
    retry_after: float | None = None
    attempts: int = 1


@dataclass(frozen=True)
class RetryEvent:
    """A retryable failure that Kliz is about to retry after *delay* seconds."""

    provider: str
    attempt: int
    delay: float
    error: ProviderError
    urls: tuple[str, ...] = ()
