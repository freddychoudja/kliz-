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

