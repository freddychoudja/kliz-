"""Google Indexing API and Search Console providers."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import SplitResult

from kliz._validation import parse_http_url
from kliz.exceptions import MissingDependencyError, ProviderError
from kliz.providers.base import BaseProvider

try:
    import google_auth_httplib2
    import httplib2
    from google.auth.exceptions import GoogleAuthError, TransportError
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as exc:  # pragma: no cover - covered by the wheel CI job
    _GOOGLE_IMPORT_ERROR: Optional[ImportError] = exc
else:
    _GOOGLE_IMPORT_ERROR = None

_DOMAIN_PROPERTY_PREFIX = "sc-domain:"


class _GoogleApiProvider(BaseProvider):
    """Lazy service-account client and error mapping shared by Google APIs."""

    api_name: str
    api_version: str
    scope: str

    def __init__(
        self,
        service_account_file: Union[str, Path],
        *,
        timeout: float,
        num_retries: int,
    ) -> None:
        if _GOOGLE_IMPORT_ERROR is not None:
            raise MissingDependencyError(
                f"{type(self).__name__} needs the Google client libraries:"
                " pip install 'kliz[google]'"
            ) from _GOOGLE_IMPORT_ERROR
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

    def _execute(self, request: Any) -> None:
        """Run a Google API request, mapping failures to :class:`ProviderError`."""

        try:
            request.execute(num_retries=self.num_retries)
        except HttpError as exc:
            status_code = int(exc.resp.status)
            retryable = status_code in {408, 429} or status_code >= 500
            raise ProviderError(
                self._rejection_message(status_code),
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

    def _rejection_message(self, status_code: int) -> str:
        return f"Google rejected the notification with HTTP {status_code}"

    def _get_service(self) -> Any:
        """Return the Google API client, building it once on first use."""

        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self) -> Any:
        """Build the authenticated Google API client.

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
                self.api_name,
                self.api_version,
                http=authorized_http,
                cache_discovery=False,
            )
        except (OSError, ValueError, GoogleAuthError) as exc:
            raise ProviderError(
                "Google service account could not be loaded",
                provider=self.name,
            ) from exc


class GoogleProvider(_GoogleApiProvider):
    """Notify Google for eligible JobPosting or BroadcastEvent pages only."""

    api_name = "indexing"
    api_version = "v3"
    scope = "https://www.googleapis.com/auth/indexing"

    def __init__(
        self,
        service_account_file: Union[str, Path],
        *,
        timeout: float = 60.0,
        num_retries: int = 2,
    ) -> None:
        super().__init__(service_account_file, timeout=timeout, num_retries=num_retries)

    def notify(self, url: str) -> bool:
        """Publish a ``URL_UPDATED`` notification to Google."""

        parse_http_url(url, require_clean=True)
        normalized_url = url.strip()
        service = self._get_service()
        self._execute(
            service.urlNotifications().publish(
                body={"url": normalized_url, "type": "URL_UPDATED"}
            )
        )
        return True


class GoogleSearchConsoleProvider(_GoogleApiProvider):
    """Resubmit a sitemap to Google Search Console, for any kind of page.

    Google offers no general "index this URL" API: the supported way to tell
    it that pages changed is to (re)submit the sitemap listing them. Every
    notification therefore resubmits ``sitemap_url``; ``notify_many`` submits
    it once for the whole batch. URLs are only checked to belong to the
    property, never sent.

    ``site_url`` is the Search Console property exactly as Google shows it:
    ``https://example.com/`` (URL-prefix) or ``sc-domain:example.com``
    (domain). The service account must be added to that property as an Owner
    or Full user.
    """

    api_name = "searchconsole"
    api_version = "v1"
    scope = "https://www.googleapis.com/auth/webmasters"

    def __init__(
        self,
        service_account_file: Union[str, Path],
        site_url: str,
        sitemap_url: Optional[str] = None,
        *,
        timeout: float = 60.0,
        num_retries: int = 2,
    ) -> None:
        super().__init__(service_account_file, timeout=timeout, num_retries=num_retries)
        self.site_url = _normalize_property(site_url)
        if sitemap_url is None:
            sitemap_url = f"{self._property_root()}sitemap.xml"
        self.sitemap_url = sitemap_url.strip()
        try:
            self.validate_url(self.sitemap_url)
        except ValueError as exc:
            raise ValueError(f"sitemap_url is invalid: {exc}") from exc

    def notify(self, url: str) -> bool:
        """Check that *url* belongs to the property, then resubmit the sitemap."""

        self.validate_url(url)
        return self._submit()

    def notify_many(self, urls: Sequence[str]) -> bool:
        """Check every URL, then resubmit the sitemap once."""

        if isinstance(urls, (str, bytes)) or not urls:
            raise ValueError("urls must be a non-empty sequence")
        for url in urls:
            self.validate_url(url)
        return self._submit()

    def validate_url(self, url: str) -> SplitResult:
        """Return *url* parsed, or raise ``ValueError`` if outside the property."""

        parsed_url = parse_http_url(url)
        host = (parsed_url.hostname or "").lower()
        if self.site_url.startswith(_DOMAIN_PROPERTY_PREFIX):
            domain = self.site_url[len(_DOMAIN_PROPERTY_PREFIX) :]
            inside = host == domain or host.endswith(f".{domain}")
        else:
            prefix = parse_http_url(self.site_url)
            inside = (
                parsed_url.scheme.lower() == prefix.scheme
                and host == prefix.hostname
                and parsed_url.port == prefix.port
                and (parsed_url.path or "/").startswith(prefix.path)
            )
        if not inside:
            raise ValueError(
                f"url is outside the Search Console property {self.site_url}"
            )
        return parsed_url

    def _submit(self) -> bool:
        service = self._get_service()
        self._execute(
            service.sitemaps().submit(siteUrl=self.site_url, feedpath=self.sitemap_url)
        )
        return True

    def _rejection_message(self, status_code: int) -> str:
        message = f"Search Console rejected the sitemap with HTTP {status_code}"
        if status_code == 403:
            return (
                f"{message}: add the service account to {self.site_url} in"
                " Search Console as an Owner or Full user"
            )
        if status_code == 404:
            return (
                f"{message}: property {self.site_url} not found; use its exact"
                " form (https://example.com/ or sc-domain:example.com)"
            )
        return message

    def _property_root(self) -> str:
        if self.site_url.startswith(_DOMAIN_PROPERTY_PREFIX):
            return f"https://{self.site_url[len(_DOMAIN_PROPERTY_PREFIX) :]}/"
        return self.site_url


def _normalize_property(site_url: str) -> str:
    if not isinstance(site_url, str) or not site_url.strip():
        raise ValueError("site_url must be a non-empty string")
    site_url = site_url.strip()
    if site_url.lower().startswith(_DOMAIN_PROPERTY_PREFIX):
        domain = site_url[len(_DOMAIN_PROPERTY_PREFIX) :].strip().lower().rstrip(".")
        if not domain or "/" in domain or ":" in domain:
            raise ValueError(
                "site_url domain property must look like sc-domain:example.com"
            )
        return f"{_DOMAIN_PROPERTY_PREFIX}{domain}"

    parsed = parse_http_url(site_url, require_clean=True)
    netloc = (parsed.hostname or "") + (f":{parsed.port}" if parsed.port else "")
    path = parsed.path if parsed.path.endswith("/") else f"{parsed.path}/"
    return f"{parsed.scheme.lower()}://{netloc}{path}"
