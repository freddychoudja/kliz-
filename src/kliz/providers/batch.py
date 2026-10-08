"""Reusable batch provider base for host-scoped indexing APIs."""

from abc import abstractmethod
from collections.abc import Sequence
from typing import Optional
from urllib.parse import SplitResult

import requests

from kliz._http import create_session
from kliz._validation import parse_http_url
from kliz.providers.base import BaseProvider


class BatchProvider(BaseProvider):
    """Provider that notifies one or many URLs belonging to the same host.

    Subclasses implement :meth:`_notify_many`. ``notify`` is implemented as a
    single-URL batch so adapters only maintain one submission path.
    """

    max_urls_per_request: int = 1

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.timeout = timeout
        self._session = create_session(session)

    def close(self) -> None:
        """Release the pooled connections held by this provider."""

        self._session.close()

    def notify(self, url: str) -> bool:
        """Notify the provider that *url* was updated."""

        return self.notify_many([url])

    def notify_many(self, urls: Sequence[str]) -> bool:
        """Submit up to ``max_urls_per_request`` URLs for the same host."""

        normalized_urls, parsed_urls = self._validate_urls(urls)
        return self._notify_many(normalized_urls, parsed_urls)

    def validate_url(self, url: str) -> SplitResult:
        """Return *url* parsed, or raise ``ValueError`` if it would be rejected.

        Orchestrators call this to drop invalid URLs one by one instead of
        failing a whole batch. Subclasses add their own per-URL rules.
        """

        return parse_http_url(url, require_clean=True)

    @abstractmethod
    def _notify_many(
        self,
        urls: list[str],
        parsed_urls: list[SplitResult],
    ) -> bool:
        """Submit an already validated same-host URL batch."""

        raise NotImplementedError

    def _validate_urls(
        self, urls: Sequence[str]
    ) -> tuple[list[str], list[SplitResult]]:
        if isinstance(urls, (str, bytes)) or not urls:
            raise ValueError("urls must be a non-empty sequence")
        if len(urls) > self.max_urls_per_request:
            raise ValueError(
                f"provider accepts at most {self.max_urls_per_request} URLs per request"
            )

        normalized_urls = [url.strip() for url in urls]
        parsed_urls = [self.validate_url(url) for url in normalized_urls]
        hosts = {parsed.hostname.lower() for parsed in parsed_urls if parsed.hostname}
        if len(hosts) != 1:
            raise ValueError("all batch URLs must belong to the same host")
        return normalized_urls, parsed_urls
