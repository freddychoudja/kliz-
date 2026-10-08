"""Result models returned by the kliz orchestrator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationResult:
    """Detailed outcome of one provider notification."""

    provider: str
    success: bool
    retryable: bool = False
    error: str | None = None
    status_code: int | None = None
    urls: tuple[str, ...] = ()
