"""Google Indexing API provider implementation."""

from pathlib import Path
from typing import Any, Union

import google_auth_httplib2
import httplib2
from google.auth.exceptions import TransportError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from kliz._validation import parse_http_url
from kliz.exceptions import ProviderError
from kliz.providers.base import BaseProvider


class GoogleProvider(BaseProvider):
    """Notify Google for eligible JobPosting or BroadcastEvent pages only."""

    scope = "https://www.googleapis.com/auth/indexing"

    def __init__(
        self,
        service_account_file: Union[str, Path],
        *,
        timeout: float = 60.0,
        num_retries: int = 2,
    ) -> None:
        if not str(service_account_file):
            raise ValueError("service_account_file must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if num_retries < 0:
            raise ValueError("num_retries must not be negative")

        credentials = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
            str(service_account_file),
            scopes=[self.scope],
        )
        authorized_http = google_auth_httplib2.AuthorizedHttp(
            credentials,
            http=httplib2.Http(timeout=timeout),
        )
        self._service: Any = build(
            "indexing",
            "v3",
            http=authorized_http,
            cache_discovery=False,
        )
        self.num_retries = num_retries

    def notify(self, url: str) -> bool:
        """Publish a ``URL_UPDATED`` notification to Google."""

        parse_http_url(url)
        normalized_url = url.strip()

        try:
            (
                self._service.urlNotifications()
                .publish(body={"url": normalized_url, "type": "URL_UPDATED"})
                .execute(num_retries=self.num_retries)
            )
        except HttpError as exc:
            status_code = int(exc.resp.status)
            retryable = status_code in {408, 429} or status_code >= 500
            raise ProviderError(
