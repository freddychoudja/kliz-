"""Public API for kliz."""

from importlib.metadata import PackageNotFoundError, version

from kliz.core import Kliz
from kliz.exceptions import KlizError, ProviderError
from kliz.providers import BaseProvider, GoogleProvider, IndexNowProvider
from kliz.results import NotificationResult

__all__ = [
    "BaseProvider",
    "GoogleProvider",
    "IndexNowProvider",
    "Kliz",
    "KlizError",
    "NotificationResult",
    "ProviderError",
]

try:
    __version__ = version("kliz")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.0.0"
