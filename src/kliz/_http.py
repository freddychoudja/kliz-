"""Shared HTTP helpers for indexing providers."""

from collections.abc import Mapping
from typing import Any, Optional

import requests

from kliz.exceptions import ProviderError

DEFAULT_SUCCESS_STATUSES: set[int] = {200, 202}


def create_session(session: Optional[requests.Session] = None) -> requests.Session:
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

    try:
        return session.post(url, json=dict(payload), timeout=timeout)
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
    success_statuses: Optional[set[int]] = None,
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
