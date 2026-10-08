"""Shared HTTP helpers for indexing providers."""

import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from kliz.exceptions import ProviderError

logger = logging.getLogger(__name__)

DEFAULT_SUCCESS_STATUSES: set[int] = {200, 202}


def create_session(session: requests.Session | None = None) -> requests.Session:
    """Return *session* or a fresh :class:`requests.Session`."""

    return session if session is not None else requests.Session()


def post_json(
    session: requests.Session,
    url: str,
    *,
    payload: Mapping[str, Any],
    timeout: float,
    provider: str,
) -> requests.Response:
    """POST JSON and map transport failures to :class:`ProviderError`."""

    return _send(
        session, "POST", url, provider=provider, json=dict(payload), timeout=timeout
    )


def get(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
    provider: str,
    allow_redirects: bool = True,
    log_url: str | None = None,
) -> requests.Response:
    """GET *url* and map transport failures to :class:`ProviderError`.

    *log_url* replaces *url* in log records, e.g. to hide a secret in it.
    """

    return _send(
        session,
        "GET",
        url,
        provider=provider,
        log_url=log_url,
        timeout=timeout,
        allow_redirects=allow_redirects,
    )


def _send(
    session: requests.Session,
    method: str,
    url: str,
    *,
    provider: str,
    log_url: str | None = None,
    **kwargs: Any,
) -> requests.Response:
    shown_url = log_url if log_url is not None else url
    try:
        if method == "POST":
            response = session.post(url, **kwargs)
        else:
            response = session.get(url, **kwargs)
    except (requests.Timeout, requests.ConnectionError) as exc:
        # Only the type: transport messages embed the URL, which may hold a secret.
        logger.debug(
            "%s: %s %s failed: %s", provider, method, shown_url, type(exc).__name__
        )
        raise ProviderError(
            f"{provider} could not be reached",
            provider=provider,
            retryable=True,
        ) from exc
    except requests.RequestException as exc:
        raise ProviderError(
            f"{provider} request failed",
            provider=provider,
        ) from exc
    logger.debug(
        "%s: %s %s -> HTTP %s", provider, method, shown_url, response.status_code
    )
    return response


def raise_for_indexing_status(
    response: requests.Response,
    *,
    provider: str,
    success_statuses: set[int] | None = None,
) -> bool:
    """Return ``True`` for accepted statuses or raise :class:`ProviderError`."""

    accepted = (
        success_statuses if success_statuses is not None else DEFAULT_SUCCESS_STATUSES
    )
    if response.status_code in accepted:
        return True

    retryable = response.status_code == 429 or response.status_code >= 500
    raise ProviderError(
        f"{provider} rejected the notification with HTTP {response.status_code}",
        provider=provider,
        retryable=retryable,
        status_code=response.status_code,
        retry_after=parse_retry_after(response.headers.get("Retry-After")),
    )


def parse_retry_after(value: object, *, now: datetime | None = None) -> float | None:
    """Return the delay in seconds from a ``Retry-After`` header, if valid.

    The header holds either a number of seconds or an HTTP date. Missing or
    malformed values give ``None``; dates in the past give ``0.0``.
    """

    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.isdigit():
        return float(text)
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    current = now if now is not None else datetime.now(timezone.utc)
    return max(0.0, (moment - current).total_seconds())
