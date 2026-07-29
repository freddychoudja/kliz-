"""Exceptions exposed by kliz."""

from typing import Optional


class KlizError(Exception):
    """Base class for all kliz-specific errors."""


class ProviderError(KlizError):
    """An indexing provider could not complete a notification."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        retryable: bool = False,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.status_code = status_code