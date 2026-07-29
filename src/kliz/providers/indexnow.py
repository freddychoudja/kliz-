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
                json=payload,
                timeout=self.timeout,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise ProviderError(
                "IndexNow could not be reached",
                provider=self.name,
                retryable=True,
            ) from exc
        except requests.RequestException as exc:
            raise ProviderError(
                "IndexNow request failed",
                provider=self.name,
            ) from exc

        if response.status_code in {200, 202}:
            return True

        retryable = response.status_code == 429 or response.status_code >= 500
        raise ProviderError(
            f"IndexNow rejected the notification with HTTP {response.status_code}",
            provider=self.name,
            retryable=retryable,
            status_code=response.status_code,
        )

    def _validate_urls(
        self, urls: Sequence[str]
    ) -> tuple[list[str], list[SplitResult]]:
        if isinstance(urls, (str, bytes)) or not urls:
            raise ValueError("urls must be a non-empty sequence")
        if len(urls) > self.max_urls_per_request:
            raise ValueError("IndexNow accepts at most 10,000 URLs per request")

        normalized_urls = [url.strip() for url in urls]
        parsed_urls = [parse_http_url(url) for url in normalized_urls]
        hosts = {parsed.hostname.lower() for parsed in parsed_urls if parsed.hostname}
        if len(hosts) != 1:
            raise ValueError("all IndexNow URLs must belong to the same host")
        return normalized_urls, parsed_urls

    def _validate_key_location(self, submitted_url: SplitResult) -> None:
        if self.key_location is None:
            return

        key_url = parse_http_url(self.key_location)
        if key_url.hostname is None or submitted_url.hostname is None:
            raise ValueError("key_location and url must include a hostname")
        if key_url.hostname.lower() != submitted_url.hostname.lower():
            raise ValueError("key_location must use the same host as the submitted URL")

        key_directory = str(PurePosixPath(key_url.path).parent)
        if key_directory == ".":
            key_directory = "/"
        normalized_directory = key_directory.rstrip("/") + "/"
        submitted_path = submitted_url.path or "/"
        if normalized_directory != "/" and not submitted_path.startswith(
            normalized_directory
        ):
            raise ValueError("url must be within the path covered by key_location")
