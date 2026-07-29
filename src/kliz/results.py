"""Result models returned by the kliz orchestrator."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NotificationResult:
    """Detailed outcome of one provider notification."""

    provider: str
    success: bool
    retryable: bool = False
    error: Optional[str] = None
    status_code: Optional[int] = None