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
