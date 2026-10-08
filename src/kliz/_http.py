"""Shared HTTP helpers for indexing providers."""

from collections.abc import Mapping
from typing import Any

import requests

from kliz.exceptions import ProviderError

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
) -> requests.Response:
    """GET *url* and map transport failures to :class:`ProviderError`."""

    return _send(
        session,
        "GET",
        url,
        provider=provider,
        timeout=timeout,
        allow_redirects=allow_redirects,
    )


def _send(
    session: requests.Session,
    method: str,
    url: str,
    *,
    provider: str,
    **kwargs: Any,
) -> requests.Response:
    try:
        if method == "POST":
            return session.post(url, **kwargs)
        return session.get(url, **kwargs)
    except (requests.Timeout, requests.ConnectionError) as exc:
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
    )
