"""Exceptions exposed by kliz."""


class KlizError(Exception):
    """Base class for all kliz-specific errors."""


class MissingDependencyError(KlizError, ImportError):
    """An optional dependency (``pip install 'kliz[extra]'``) is not installed."""


class ProviderError(KlizError):
    """An indexing provider could not complete a notification."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.status_code = status_code
