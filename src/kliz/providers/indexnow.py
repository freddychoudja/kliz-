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
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if key_location is not None:
            parse_http_url(key_location)

        self.api_key = api_key
        self.key_location = key_location
        self.timeout = timeout

    def notify(self, url: str) -> bool:
        """Submit one updated URL to IndexNow."""

        return self.notify_many([url])

    def notify_many(self, urls: Sequence[str]) -> bool:
        """Submit up to 10,000 URLs belonging to the same host."""

        normalized_urls, parsed_urls = self._validate_urls(urls)
        host = parsed_urls[0].hostname
        if host is None:  # Defensive: parse_http_url already enforces this.
            raise ValueError("url must include a hostname")

        self._validate_key_location(parsed_urls[0])
        payload: dict[str, PayloadValue] = {
            "host": host,
            "key": self.api_key,
            "urlList": normalized_urls,
        }
        if self.key_location:
            payload["keyLocation"] = self.key_location

        try:
            response = requests.post(
                self.endpoint,
