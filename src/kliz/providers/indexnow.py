"""IndexNow provider implementation."""

import logging
import re
import secrets
import string
from pathlib import PurePosixPath
from urllib.parse import SplitResult, urlsplit

import requests

from kliz._http import get, post_json, raise_for_indexing_status
from kliz._validation import normalize_url, parse_http_url
from kliz.exceptions import ProviderError
from kliz.providers.batch import BatchProvider

PayloadValue = str | list[str]

logger = logging.getLogger(__name__)

_KEY_ALPHABET = string.ascii_letters + string.digits


class IndexNowProvider(BatchProvider):
    """Notify search engines that support the IndexNow protocol."""

    endpoint = "https://api.indexnow.org/indexnow"
    max_urls_per_request = 10_000
    _key_pattern = re.compile(r"^[A-Za-z0-9-]{8,128}$")

    def __init__(
        self,
        api_key: str,
        key_location: str | None = None,
        timeout: float = 10.0,
        *,
        session: requests.Session | None = None,
        allow_query: bool = False,
    ) -> None:
        if not isinstance(api_key, str) or not self._key_pattern.fullmatch(api_key):
            raise ValueError(
                "api_key must contain 8 to 128 letters, numbers, or dashes"
            )
        if key_location is not None:
            parse_http_url(key_location, require_clean=True)

        super().__init__(timeout=timeout, session=session, allow_query=allow_query)
        self.api_key = api_key
        self.key_location = key_location

    @staticmethod
    def generate_key(length: int = 32) -> str:
        """Return a new random IndexNow key of *length* letters and digits."""

        if isinstance(length, bool) or not isinstance(length, int):
            raise TypeError("length must be an integer")
        if not 8 <= length <= 128:
            raise ValueError("length must be between 8 and 128")
        return "".join(secrets.choice(_KEY_ALPHABET) for _ in range(length))

    def key_file_url(self, site_url: str | None = None) -> str:
        """Return where engines look for the key file.

        That is ``key_location`` when set, otherwise ``<site>/<key>.txt`` at the
        root of *site_url*, as the IndexNow protocol specifies.
        """

        if self.key_location is not None:
            return self.key_location
        if site_url is None:
            raise ValueError("site_url is required when key_location is not set")
        site = parse_http_url(site_url)
        return f"{site.scheme.lower()}://{site.netloc}/{self.api_key}.txt"

    def verify_key(self, site_url: str | None = None) -> str:
        """Check that the key file is published the way engines expect.

        Returns the verified key file URL, or raises :class:`ProviderError`
        describing what an engine would get instead of the key. Redirects are
        not followed: engines are not required to follow them. Messages and
        logs show the key as ``<key>``.
        """

        location = self.key_file_url(site_url)
        shown = self._redact(location)
        response = get(
            self._session,
            location,
            timeout=self.timeout,
            provider=self.name,
            allow_redirects=False,
            log_url=shown,
        )
        status_code = response.status_code
        if 300 <= status_code < 400:
            target = self._redact(response.headers.get("Location", "another URL"))
            raise ProviderError(
                f"key file {shown} redirects (HTTP {status_code}) to {target};"
                " serve it directly with HTTP 200",
                provider=self.name,
                status_code=status_code,
            )
        if status_code != 200:
            raise ProviderError(
                f"key file {shown} returned HTTP {status_code}",
                provider=self.name,
                retryable=status_code == 429 or status_code >= 500,
                status_code=status_code,
            )

        body = response.text.strip()
        if body == self.api_key:
            return location
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" in content_type or body.startswith("<"):
            raise ProviderError(
                f"key file {shown} returned an HTML page instead of the key;"
                " the file is probably missing and the site answers 200 for"
                " unknown paths",
                provider=self.name,
                status_code=status_code,
            )
        raise ProviderError(
            f"key file {shown} does not contain the API key",
            provider=self.name,
            status_code=status_code,
        )

    def _redact(self, text: str) -> str:
        return text.replace(self.api_key, "<key>")

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

        logger.debug(
            "%s: submitting %d URL(s) for %s to %s",
            self.name,
            len(urls),
            host,
            self.endpoint,
        )
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

        key_url = urlsplit(normalize_url(self.key_location))
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
