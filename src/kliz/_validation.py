"""Shared input validation helpers."""

import ipaddress
import re
from urllib.parse import SplitResult, quote, urlsplit, urlunsplit

_DEFAULT_PORTS = {"http": 80, "https": 443}
_HOST_LABEL_RE = re.compile(r"[a-z0-9_-]{1,63}")
# RFC 3986 reserved and unreserved characters, plus "%" to keep escapes intact.
_URL_SAFE = "/:@!$&'()*+,;=-._~%?"


def parse_http_url(url: str, *, require_clean: bool = False) -> SplitResult:
    """Return a parsed absolute HTTP(S) URL or raise ``ValueError``.

    A fragment (``#...``) is always rejected because it is never sent to the
    server: ``page`` and ``page#top`` address the same resource, so a fragment
    can never be meaningful for indexing and may even carry auth tokens.

    A query string (``?...``) is rejected only when ``require_clean`` is true.
    The server does receive the query, so it can address a real resource;
    whether a clean canonical URL is mandatory is the caller's decision.
    """

    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")

    normalized_url = url.strip()
    authority = re.match(r"https?://([^/?#]*)", normalized_url, re.IGNORECASE)
    if authority and any(ord(char) < 32 or ord(char) == 127 for char in authority[1]):
        raise ValueError("url has an invalid hostname")
    parsed_url = urlsplit(normalized_url)
    if parsed_url.scheme.lower() not in {"http", "https"}:
        raise ValueError("url must use the http or https scheme")
    if not parsed_url.hostname:
        raise ValueError("url must include a hostname")
    _normalize_hostname(parsed_url.hostname)
    if parsed_url.username is not None or parsed_url.password is not None:
        raise ValueError("url must not contain credentials")
    if parsed_url.fragment:
        raise ValueError("url must not contain a fragment")
    if require_clean and parsed_url.query:
        raise ValueError("url must not contain a query string")

    return parsed_url


def _normalize_hostname(host: str) -> str:
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in host):
        raise ValueError("url has an invalid hostname")
    if "%" in host:
        raise ValueError("url has an invalid hostname")
    if ":" in host:
        try:
            ipaddress.IPv6Address(host)
        except ValueError as exc:
            raise ValueError("url has an invalid hostname") from exc
        return host
    try:
        host = host.encode("idna").decode("ascii").lower().removesuffix(".")
    except UnicodeError as exc:
        # The codec also refuses empty or overlong labels in plain ASCII names.
        kind = "hostname" if host.isascii() else "internationalized hostname"
        raise ValueError(f"url has an invalid {kind}") from exc
    if (
        not host
        or len(host) > 253
        or not all(_HOST_LABEL_RE.fullmatch(label) for label in host.split("."))
    ):
        raise ValueError("url has an invalid hostname")
    return host


def normalize_url(url: str) -> str:
    """Return the canonical form of an absolute HTTP(S) URL.

    The scheme and host are lowercased, internationalized hostnames are
    converted to their ASCII (punycode) form, default ports and a trailing
    dot on the host are dropped, an empty path becomes ``/`` and characters
    not allowed in a URL (non-ASCII, spaces) are percent-encoded. Existing
    escapes, case and parameter order are kept, since servers may treat them
    as significant. Raises ``ValueError`` for URLs that
    :func:`parse_http_url` rejects.
    """

    parsed = parse_http_url(url)
    scheme = parsed.scheme.lower()
    host = _normalize_hostname(parsed.hostname or "")
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port
    netloc = host if port in (None, _DEFAULT_PORTS[scheme]) else f"{host}:{port}"
    path = quote(parsed.path or "/", safe=_URL_SAFE)
    query = quote(parsed.query, safe=_URL_SAFE)
    return urlunsplit((scheme, netloc, path, query, ""))
