"""Read page URLs from XML sitemaps and sitemap indexes."""

import gzip
import io
import logging
import zlib
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element

import requests
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from kliz.exceptions import KlizError

logger = logging.getLogger(__name__)

SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
# Sitemaps protocol limit for one (uncompressed) sitemap file.
MAX_SITEMAP_BYTES = 50 * 1024 * 1024
MAX_INDEX_DEPTH = 3

Since = date | datetime


class SitemapError(KlizError):
    """A sitemap could not be fetched, decompressed or parsed."""


def read_sitemap(
    source: str | Path,
    *,
    since: Since | None = None,
    session: requests.Session | None = None,
    timeout: float = 10.0,
) -> list[str]:
    """Return the page URLs listed in a sitemap, in document order.

    *source* is an http(s) URL or a local file path; gzip-compressed files are
    detected automatically. Sitemap indexes are followed (child sitemaps are
    fetched over HTTP). Image, video and hreflang entries are ignored: only
    ``<url><loc>`` values are returned, stripped and deduplicated.

    With *since*, only entries whose ``<lastmod>`` is on or after it are kept;
    entries without a usable ``<lastmod>`` are kept, since they may have
    changed. A naive *since* is interpreted as UTC.
    """

    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")

    threshold = _to_utc(since) if since is not None else None
    owned_session = session is None
    http = session if session is not None else requests.Session()
    try:
        urls: dict[str, None] = {}
        _collect(str(source), threshold, http, timeout, urls, set(), depth=0)
        logger.info("read %d page URL(s) from %s", len(urls), source)
        return list(urls)
    finally:
        if owned_session:
            http.close()


def _collect(
    source: str,
    threshold: datetime | None,
    session: requests.Session,
    timeout: float,
    urls: dict[str, None],
    visited: set[str],
    *,
    depth: int,
) -> None:
    if source in visited:
        return
    visited.add(source)
    logger.debug("reading sitemap %s", source)

    root = _parse(_load(source, session, timeout), source)
    kind = _local_name(root)
    if kind == "urlset":
        for loc, lastmod in _entries(root, "url"):
            if _is_recent(lastmod, threshold):
                urls.setdefault(loc)
    elif kind == "sitemapindex":
        if depth >= MAX_INDEX_DEPTH:
            raise SitemapError(f"{source}: sitemap indexes are nested too deeply")
        for loc, lastmod in _entries(root, "sitemap"):
            if not loc.lower().startswith(("http://", "https://")):
                raise SitemapError(f"{source}: child sitemap is not http(s): {loc}")
            if _is_recent(lastmod, threshold):
                _collect(
                    loc, threshold, session, timeout, urls, visited, depth=depth + 1
                )
    else:
        raise SitemapError(f"{source}: not a sitemap (root element <{root.tag}>)")


def _load(source: str, session: requests.Session, timeout: float) -> bytes:
    if source.lower().startswith(("http://", "https://")):
        data = _fetch(source, session, timeout)
    else:
        try:
            with open(source, "rb") as handle:
                data = handle.read(MAX_SITEMAP_BYTES + 1)
        except OSError as exc:
            raise SitemapError(f"cannot read {source}: {exc}") from exc
        if len(data) > MAX_SITEMAP_BYTES:
            raise SitemapError(f"{source}: sitemap exceeds {MAX_SITEMAP_BYTES} bytes")
    return _decompress(data, source)


def _fetch(url: str, session: requests.Session, timeout: float) -> bytes:
    try:
        with session.get(url, timeout=timeout, stream=True) as response:
            if response.status_code != 200:
                raise SitemapError(f"{url}: HTTP {response.status_code}")
            body = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                body.extend(chunk)
                if len(body) > MAX_SITEMAP_BYTES:
                    raise SitemapError(
                        f"{url}: sitemap exceeds {MAX_SITEMAP_BYTES} bytes"
                    )
            return bytes(body)
    except requests.RequestException as exc:
        raise SitemapError(f"{url}: could not be fetched ({exc})") from exc


def _decompress(data: bytes, source: str) -> bytes:
    if not data.startswith(b"\x1f\x8b"):
        return data
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as archive:
            inflated = archive.read(MAX_SITEMAP_BYTES + 1)
    except (OSError, EOFError, zlib.error) as exc:
        raise SitemapError(f"{source}: invalid gzip data") from exc
    if len(inflated) > MAX_SITEMAP_BYTES:
        raise SitemapError(f"{source}: sitemap exceeds {MAX_SITEMAP_BYTES} bytes")
    return inflated


def _parse(data: bytes, source: str) -> Element:
    if data.lstrip()[:14].lower().startswith((b"<!doctype html", b"<html")):
        raise SitemapError(
            f"{source}: returned an HTML page, not a sitemap; the file is probably"
            " missing and the site answers 200 for unknown paths"
        )
    try:
        return fromstring(data, forbid_dtd=True)
    except (ParseError, DefusedXmlException) as exc:
        raise SitemapError(f"{source}: invalid sitemap XML ({exc})") from exc


def _local_name(element: Element) -> str | None:
    """Return the tag name if it is in the sitemap namespace (or none)."""

    tag = element.tag
    if not isinstance(tag, str):
        return None
    if tag.startswith("{"):
        namespace, _, name = tag[1:].partition("}")
        return name if namespace == SITEMAP_NAMESPACE else None
    return tag


def _entries(root: Element, entry_tag: str) -> list[tuple[str, str | None]]:
    entries: list[tuple[str, str | None]] = []
    for entry in root:
        if _local_name(entry) != entry_tag:
            continue
        loc: str | None = None
        lastmod: str | None = None
        for child in entry:
            name = _local_name(child)
            if name == "loc" and child.text and child.text.strip():
                loc = child.text.strip()
            elif name == "lastmod" and child.text:
                lastmod = child.text.strip()
        if loc:
            entries.append((loc, lastmod))
    return entries


def _is_recent(lastmod: str | None, threshold: datetime | None) -> bool:
    if threshold is None or lastmod is None:
        return True
    parsed = _parse_lastmod(lastmod)
    return parsed is None or parsed >= threshold


def _parse_lastmod(value: str) -> datetime | None:
    """Parse a W3C datetime (``YYYY``, ``YYYY-MM``, date or full datetime)."""

    text = value.strip()
    try:
        if len(text) == 4:
            return datetime(int(text), 1, 1, tzinfo=timezone.utc)
        if len(text) == 7:
            return datetime(int(text[:4]), int(text[5:7]), 1, tzinfo=timezone.utc)
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        return _to_utc(datetime.fromisoformat(text))
    except ValueError:
        return None


def _to_utc(moment: Since) -> datetime:
    if not isinstance(moment, datetime):
        moment = datetime(moment.year, moment.month, moment.day)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)
