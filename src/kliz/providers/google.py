"""Google Indexing API provider implementation."""

from pathlib import Path
from typing import Any, Optional, Union

import google_auth_httplib2
import httplib2
from google.auth.exceptions import GoogleAuthError, TransportError
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

        self.service_account_file = service_account_file
        self.timeout = timeout
        self.num_retries = num_retries
        self._service: Optional[Any] = None

    def notify(self, url: str) -> bool:
        """Publish a ``URL_UPDATED`` notification to Google."""

        parse_http_url(url, require_clean=True)
        normalized_url = url.strip()
        service = self._get_service()

        try:
            (
                service.urlNotifications()
                .publish(body={"url": normalized_url, "type": "URL_UPDATED"})
                .execute(num_retries=self.num_retries)
            )
        except HttpError as exc:
            status_code = int(exc.resp.status)
            retryable = status_code in {408, 429} or status_code >= 500
            raise ProviderError(
                f"Google rejected the notification with HTTP {status_code}",
                provider=self.name,
                retryable=retryable,
                status_code=status_code,
            ) from exc
        except (TransportError, httplib2.HttpLib2Error, OSError) as exc:
            raise ProviderError(
                "Google could not be reached",
                provider=self.name,
                retryable=True,
            ) from exc
        return True

    def _get_service(self) -> Any:
        """Return the Google API client, building it once on first use."""

        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self) -> Any:
        """Build the authenticated Google Indexing API client.

        Only successes are cached: if building fails the provider retries on
        a later notification instead of remaining broken forever.
        """

        try:
            credentials = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
                str(self.service_account_file),
                scopes=[self.scope],
            )
            authorized_http = google_auth_httplib2.AuthorizedHttp(
                credentials,
                http=httplib2.Http(timeout=self.timeout),
            )
            return build(
                "indexing",
                "v3",
                http=authorized_http,
                cache_discovery=False,
            )
        except (OSError, ValueError, GoogleAuthError) as exc:
            raise ProviderError(
                "Google service account could not be loaded",
                provider=self.name,
            ) from exc
