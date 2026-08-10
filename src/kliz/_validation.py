"""Shared input validation helpers."""

from urllib.parse import SplitResult, urlsplit


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
