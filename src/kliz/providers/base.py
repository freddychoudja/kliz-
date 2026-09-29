"""Contracts implemented by indexing providers."""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Strategy interface for a search-engine indexing provider."""

    @property
    def name(self) -> str:
        """Return the provider name used in orchestration results."""

        return self.__class__.__name__

    @abstractmethod
    def notify(self, url: str) -> bool:
        """Notify the provider that *url* was updated.

        Implementations return ``True`` after a successful notification and
        raise :class:`kliz.exceptions.ProviderError` when the remote service
        rejects the request or cannot be reached.
        """

        raise NotImplementedError

    def close(self) -> None:  # noqa: B027
        """Release resources held by this provider.

        The default implementation is a no-op.  Subclasses that hold
        persistent connections (HTTP sessions, gRPC channels, etc.)
        should override this method.
        """
