"""CLI entry point for kliz."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from . import __version__
from ._config import ConfigurationError, find_config, load_config
from .core import Kliz
from .exceptions import MissingDependencyError, ProviderError
from .providers import (
    BaseProvider,
    GoogleSearchConsoleProvider,
    IndexNowProvider,
)
from .sitemap import SitemapError, read_sitemap

logger = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "on"}


class _TimeoutKwargs(TypedDict, total=False):
    timeout: float


def _timeout(args: argparse.Namespace) -> _TimeoutKwargs:
    """Return ``{"timeout": ...}`` when --timeout is set, for provider kwargs."""

    return {} if args.timeout is None else {"timeout": args.timeout}


def _load_cli_config(arguments: list[str]) -> dict[str, Any]:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config")
    known, _ = pre_parser.parse_known_args(arguments)
    path = find_config(known.config, Path.cwd())
    return load_config(path) if path is not None else {}


def _setting(config: Mapping[str, Any], key: str, env: str) -> Any:
    """Return the environment value for *key* if set, else the config value.

    A set environment variable (including the empty string) takes precedence.
    Falsy config values such as ``0`` or ``False`` are preserved.
    """

    value = os.environ.get(env)
    if value is not None:
        return value
    return config.get(key)


def _build_parser(config: Mapping[str, Any] | None = None) -> argparse.ArgumentParser:
    config = config or {}
    env_allow_query = os.environ.get("KLIZ_ALLOW_QUERY")
    parser = argparse.ArgumentParser(
        prog="kliz",
        description=(
            "Notify search engines (IndexNow, Google Search Console) that pages"
            " were created or updated."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        default=None,
        help="Settings file (default: ./kliz.toml, else [tool.kliz] in"
        " ./pyproject.toml); flags and KLIZ_* env vars take precedence",
    )
    parser.add_argument(
        "--indexnow-api-key",
        default=_setting(config, "indexnow_api_key", "KLIZ_INDEXNOW_API_KEY"),
        help="IndexNow API key (KLIZ_INDEXNOW_API_KEY env var)",
    )
    parser.add_argument(
        "--indexnow-key-location",
        default=_setting(config, "indexnow_key_location", "KLIZ_INDEXNOW_KEY_LOCATION"),
        help="URL where the IndexNow key file is hosted",
    )
    parser.add_argument(
        "--google-service-account-file",
        default=_setting(
            config, "google_service_account_file", "KLIZ_GOOGLE_SERVICE_ACCOUNT_FILE"
        ),
        help="Path to the Google service account JSON file (Indexing API: job"
        " posting and livestream pages only)",
    )
    parser.add_argument(
        "--gsc-site",
        default=_setting(config, "gsc_site", "KLIZ_GSC_SITE"),
        help="Search Console property, e.g. https://example.com/ or"
        " sc-domain:example.com (KLIZ_GSC_SITE env var)",
    )
    parser.add_argument(
        "--gsc-sitemap",
        default=_setting(config, "gsc_sitemap", "KLIZ_GSC_SITEMAP"),
        help="Sitemap URL to resubmit to Search Console (default: the --sitemap"
        " URL, else <property>/sitemap.xml)",
    )
    parser.add_argument(
        "--gsc-service-account-file",
        default=_setting(
            config, "gsc_service_account_file", "KLIZ_GSC_SERVICE_ACCOUNT_FILE"
        ),
        help="Service account JSON file allowed on the Search Console property",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=(
            1
            if (max_attempts := _setting(config, "max_attempts", "KLIZ_MAX_ATTEMPTS"))
            is None
            else max_attempts
        ),
        help="Attempts per notification for temporary failures (429, 5xx,"
        " network), honoring Retry-After; default 1 (KLIZ_MAX_ATTEMPTS env var)",
    )
    # ... (rest of file would be here, but truncated for this example; use full in real call)
