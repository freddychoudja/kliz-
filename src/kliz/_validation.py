"""Shared input validation helpers."""

from urllib.parse import SplitResult, urlsplit


def parse_http_url(url: str) -> SplitResult:
    """Return a parsed absolute HTTP(S) URL or raise ``ValueError``."""

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

    return parsed_url