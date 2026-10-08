"""Public API for kliz."""

from importlib.metadata import PackageNotFoundError, version

from kliz._validation import normalize_url
from kliz.core import Kliz
from kliz.exceptions import KlizError, MissingDependencyError, ProviderError
from kliz.providers import (
    BaseProvider,
    BatchProvider,
    GoogleProvider,
    GoogleSearchConsoleProvider,
    IndexNowProvider,
)
from kliz.results import NotificationResult
from kliz.sitemap import SitemapError, read_sitemap

__all__ = [
    "BaseProvider",
    "BatchProvider",
    "GoogleProvider",
    "GoogleSearchConsoleProvider",
    "IndexNowProvider",
    "Kliz",
    "KlizError",
    "MissingDependencyError",
    "NotificationResult",
    "ProviderError",
    "SitemapError",
    "normalize_url",
    "read_sitemap",
]

try:
    __version__ = version("kliz")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.0.0"
