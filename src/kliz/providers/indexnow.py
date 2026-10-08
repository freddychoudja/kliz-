"""IndexNow provider implementation."""

import re
from pathlib import PurePosixPath
from typing import Optional, Union
from urllib.parse import SplitResult

import requests

from kliz._http import post_json, raise_for_indexing_status
from kliz._validation import parse_http_url
from kliz.providers.batch import BatchProvider

PayloadValue = Union[str, list[str]]


class IndexNowProvider(BatchProvider):
    """Notify search engines that support the IndexNow protocol."""

    endpoint = "https://api.indexnow.org/indexnow"
    max_urls_per_request = 10_000
    _key_pattern = re.compile(r"^[A-Za-z0-9-]{8,128}$")

    def __init__(
        self,
        api_key: str,
        key_location: Optional[str] = None,
        timeout: float = 10.0,
        *,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not isinstance(api_key, str) or not self._key_pattern.fullmatch(api_key):
            raise ValueError(
                "api_key must contain 8 to 128 letters, numbers, or dashes"
            )
        if key_location is not None:
            parse_http_url(key_location, require_clean=True)

        super().__init__(timeout=timeout, session=session)
        self.api_key = api_key
        self.key_location = key_location

    def _notify_many(
        self,
        urls: list[str],
        parsed_urls: list[SplitResult],
    ) -> bool:
        host = parsed_urls[0].hostname
        if host is None:  # Defensive: parse_http_url already enforces this.
            raise ValueError("url must include a hostname")

        payload: dict[str, PayloadValue] = {
            "host": host,
            "key": self.api_key,
            "urlList": urls,
        }
        if self.key_location:
            payload["keyLocation"] = self.key_location

        response = post_json(
            self._session,
            self.endpoint,
            payload=payload,
            timeout=self.timeout,
            provider=self.name,
        )
        return raise_for_indexing_status(response, provider=self.name)

    def validate_url(self, url: str) -> SplitResult:
        """Also reject URLs outside the host and path covered by ``key_location``."""

        parsed_url = super().validate_url(url)
        self._validate_key_location(parsed_url)
        return parsed_url

    def _validate_key_location(self, submitted_url: SplitResult) -> None:
        if self.key_location is None:
            return

        key_url = parse_http_url(self.key_location, require_clean=True)
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
