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
