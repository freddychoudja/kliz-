"""Shared input validation helpers."""

from urllib.parse import SplitResult, quote, urlsplit, urlunsplit

_DEFAULT_PORTS = {"http": 80, "https": 443}
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
    parsed_url = urlsplit(normalized_url)
    if parsed_url.scheme.lower() not in {"http", "https"}:
        raise ValueError("url must use the http or https scheme")
    if not parsed_url.hostname:
        raise ValueError("url must include a hostname")
    if parsed_url.username is not None or parsed_url.password is not None:
        raise ValueError("url must not contain credentials")
    if parsed_url.fragment:
        raise ValueError("url must not contain a fragment")
    if require_clean and parsed_url.query:
        raise ValueError("url must not contain a query string")

    return parsed_url


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
    host = (parsed.hostname or "").rstrip(".")
    if not host.isascii():
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("url has an invalid internationalized hostname") from exc
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port
    netloc = host if port in (None, _DEFAULT_PORTS[scheme]) else f"{host}:{port}"
    path = quote(parsed.path or "/", safe=_URL_SAFE)
    query = quote(parsed.query, safe=_URL_SAFE)
    return urlunsplit((scheme, netloc, path, query, ""))
