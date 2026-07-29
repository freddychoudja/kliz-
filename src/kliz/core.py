"""Provider orchestration for kliz."""

from collections import Counter
from collections.abc import Iterable

from kliz.exceptions import ProviderError
from kliz.providers.base import BaseProvider
from kliz.results import NotificationResult


class Kliz:
    """Dispatch indexing notifications to a collection of providers."""

    def __init__(self, providers: Iterable[BaseProvider]) -> None:
        if isinstance(providers, (str, bytes)):
            raise TypeError("providers must be an iterable of BaseProvider instances")

        provider_list = list(providers)
        if not all(isinstance(provider, BaseProvider) for provider in provider_list):
            raise TypeError("every provider must inherit from BaseProvider")

        self.providers = tuple(provider_list)

    def notify_all(self, url: str) -> dict[str, bool]:
        """Notify every provider and return simple boolean statuses."""

        return {
            name: result.success
            for name, result in self.notify_all_detailed(url).items()
        }

    def notify_all_detailed(self, url: str) -> dict[str, NotificationResult]:
        """Notify all providers without hiding error and retry information."""

        results: dict[str, NotificationResult] = {}
        for provider, result_name in zip(self.providers, self._result_names()):
            try:
                success = bool(provider.notify(url))
                results[result_name] = NotificationResult(
                    provider=provider.name,
                    success=success,
                    error=None if success else "provider returned False",
                )
            except ProviderError as exc:
                results[result_name] = NotificationResult(
                    provider=provider.name,
                    success=False,
                    retryable=exc.retryable,
                    error=str(exc),
                    status_code=exc.status_code,
                )
            except Exception as exc:
                results[result_name] = NotificationResult(
                    provider=provider.name,
                    success=False,
                    error=str(exc) or exc.__class__.__name__,
                )
        return results

    def _result_names(self) -> list[str]:
        counts: Counter[str] = Counter()
        names: list[str] = []
        for provider in self.providers:
            counts[provider.name] += 1
            occurrence = counts[provider.name]
            suffix = "" if occurrence == 1 else f"#{occurrence}"
            names.append(f"{provider.name}{suffix}")
        return names
