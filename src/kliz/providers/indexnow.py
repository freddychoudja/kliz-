"""IndexNow provider implementation."""

import re
from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Optional, Union
from urllib.parse import SplitResult

import requests

from kliz._validation import parse_http_url
from kliz.exceptions import ProviderError
from kliz.providers.base import BaseProvider

PayloadValue = Union[str, list[str]]


class IndexNowProvider(BaseProvider):
    """Notify search engines that support the IndexNow protocol."""

    endpoint = "https://api.indexnow.org/indexnow"
    max_urls_per_request = 10_000
    _key_pattern = re.compile(r"^[A-Za-z0-9-]{8,128}$")

    def __init__(
        self,
        api_key: str,
        key_location: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        if not isinstance(api_key, str) or not self._key_pattern.fullmatch(api_key):
            raise ValueError(
                "api_key must contain 8 to 128 letters, numbers, or dashes"
            )
