"""Public API for kliz."""

from importlib.metadata import PackageNotFoundError, version

from kliz.core import Kliz
from kliz.exceptions import KlizError, ProviderError
from kliz.providers import (
    BaseProvider,
    BatchProvider,
    GoogleProvider,
    IndexNowProvider,
)
from kliz.results import NotificationResult
from kliz.sitemap import SitemapError, read_sitemap

__all__ = [
    "BaseProvider",
    "BatchProvider",
    "GoogleProvider",
    "IndexNowProvider",
    "Kliz",
    "KlizError",
    "NotificationResult",
    "ProviderError",
    "SitemapError",
    "read_sitemap",
]

try:
    __version__ = version("kliz")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.0.0"
