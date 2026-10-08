"""Tests for sitemap reading."""

import gzip
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from kliz import SitemapError, read_sitemap

NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'


def urlset(*entries: str) -> bytes:
    return f'<?xml version="1.0"?><urlset {NS}>{"".join(entries)}</urlset>'.encode()


def url(loc: str, lastmod: str = "") -> str:
    mod = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    return f"<url><loc>{loc}</loc>{mod}</url>"


def index(*entries: tuple[str, str]) -> bytes:
    body = "".join(
        f"<sitemap><loc>{loc}</loc>"
        + (f"<lastmod>{mod}</lastmod>" if mod else "")
        + "</sitemap>"
        for loc, mod in entries
    )
    return f"<sitemapindex {NS}>{body}</sitemapindex>".encode()


def http_session(pages: dict[str, tuple[int, bytes]]) -> MagicMock:
    session = MagicMock(spec=requests.Session)

    def get(target: str, **kwargs: object) -> MagicMock:
        status_code, body = pages[target]
        response = MagicMock()
        response.status_code = status_code
        response.iter_content.return_value = [body]
        response.__enter__.return_value = response
        return response

    session.get.side_effect = get
    return session


def write(tmp_path: Path, data: bytes, name: str = "sitemap.xml") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_reads_page_urls_and_ignores_images_and_hreflang(tmp_path: Path) -> None:
    data = (
        f'<urlset {NS} xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
        ' xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        "<url><loc>https://a.example/</loc>"
        '<xhtml:link rel="alternate" hreflang="fr" href="https://a.example/fr"/>'
        "<image:image><image:loc>https://a.example/p.webp</image:loc></image:image>"
        "</url>"
        "<url><loc>\n  https://a.example/cv  \n</loc></url>"
        "<url><loc>https://a.example/</loc></url>"
        "<url><loc>   </loc></url>"
        "<!-- comment -->"
        "</urlset>"
    ).encode()

    assert read_sitemap(write(tmp_path, data)) == [
        "https://a.example/",
        "https://a.example/cv",
    ]


def test_accepts_sitemaps_without_namespace(tmp_path: Path) -> None:
    data = b"<urlset><url><loc>https://a.example/x</loc></url></urlset>"

    assert read_sitemap(str(write(tmp_path, data))) == ["https://a.example/x"]


def test_ignores_elements_from_foreign_namespaces(tmp_path: Path) -> None:
    data = (
        f'<urlset {NS} xmlns:o="urn:other">'
        "<o:url><o:loc>https://a.example/other</o:loc></o:url>"
        "<url><loc>https://a.example/real</loc></url></urlset>"
    ).encode()

    assert read_sitemap(write(tmp_path, data)) == ["https://a.example/real"]


def test_reads_gzip_files(tmp_path: Path) -> None:
    data = gzip.compress(urlset(url("https://a.example/gz")))

    assert read_sitemap(write(tmp_path, data, "sitemap.xml.gz")) == [
        "https://a.example/gz"
    ]


def test_fetches_over_http_and_follows_sitemap_indexes() -> None:
    session = http_session(
        {
            "https://a.example/sitemap.xml": (
                200,
                index(
                    ("https://a.example/pages.xml", ""),
                    ("https://a.example/posts.xml.gz", ""),
                ),
            ),
            "https://a.example/pages.xml": (200, urlset(url("https://a.example/p"))),
            "https://a.example/posts.xml.gz": (
                200,
                gzip.compress(urlset(url("https://a.example/b"))),
            ),
        }
    )

    urls = read_sitemap("https://a.example/sitemap.xml", session=session, timeout=3)

    assert urls == ["https://a.example/p", "https://a.example/b"]
    session.get.assert_any_call("https://a.example/sitemap.xml", timeout=3, stream=True)
    session.close.assert_not_called()


def test_sitemap_index_cycles_are_visited_once() -> None:
    session = http_session(
        {
            "https://a.example/a.xml": (200, index(("https://a.example/b.xml", ""))),
            "https://a.example/b.xml": (200, index(("https://a.example/a.xml", ""))),
        }
    )

    assert read_sitemap("https://a.example/a.xml", session=session) == []
    assert session.get.call_count == 2


def test_rejects_deeply_nested_indexes() -> None:
    pages = {
        f"https://a.example/{i}.xml": (
            200,
            index((f"https://a.example/{i + 1}.xml", "")),
        )
        for i in range(5)
    }

    with pytest.raises(SitemapError, match="nested too deeply"):
        read_sitemap("https://a.example/0.xml", session=http_session(pages))


def test_rejects_non_http_child_sitemaps(tmp_path: Path) -> None:
    path = write(tmp_path, index(("file:///etc/passwd", "")))

    with pytest.raises(SitemapError, match="not http"):
        read_sitemap(path)


def test_since_filters_on_lastmod_formats(tmp_path: Path) -> None:
    data = urlset(
        url("https://a.example/old-date", "2026-09-30"),
        url("https://a.example/new-date", "2026-10-01"),
        url("https://a.example/new-datetime", "2026-10-02T08:00:00Z"),
        url("https://a.example/old-offset", "2026-10-01T01:00:00+02:00"),
        url("https://a.example/old-year", "2025"),
        url("https://a.example/old-month", "2026-09"),
        url("https://a.example/invalid", "yesterday"),
        url("https://a.example/missing"),
    )

    urls = read_sitemap(write(tmp_path, data), since=date(2026, 10, 1))

    assert urls == [
        "https://a.example/new-date",
        "https://a.example/new-datetime",
        "https://a.example/invalid",
        "https://a.example/missing",
    ]


def test_since_accepts_aware_datetimes(tmp_path: Path) -> None:
    data = urlset(url("https://a.example/x", "2026-10-01T10:00:00+00:00"))
    plus_two = timezone(timedelta(hours=2))

    assert read_sitemap(
        write(tmp_path, data), since=datetime(2026, 10, 1, 12, 0, tzinfo=plus_two)
    ) == ["https://a.example/x"]
    assert (
        read_sitemap(
            write(tmp_path, data), since=datetime(2026, 10, 1, 12, 1, tzinfo=plus_two)
        )
        == []
    )


def test_since_skips_child_sitemaps_not_modified_since() -> None:
    session = http_session(
        {
            "https://a.example/index.xml": (
                200,
                index(
                    ("https://a.example/old.xml", "2026-01-01"),
                    ("https://a.example/new.xml", "2026-10-05"),
                ),
            ),
            "https://a.example/new.xml": (
                200,
                urlset(url("https://a.example/n", "2026-10-05")),
            ),
        }
    )

    urls = read_sitemap(
        "https://a.example/index.xml", since=date(2026, 10, 1), session=session
    )

    assert urls == ["https://a.example/n"]
    assert session.get.call_count == 2


def test_detects_html_pages_served_instead_of_a_sitemap(tmp_path: Path) -> None:
    path = write(tmp_path, b"\n  <!DOCTYPE html><html><body>home</body></html>")

    with pytest.raises(SitemapError, match="HTML page, not a sitemap"):
        read_sitemap(path)


def test_forbids_dtds_to_block_entity_expansion_attacks(tmp_path: Path) -> None:
    data = (
        b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        b'<!ENTITY lol2 "&lol;&lol;&lol;">]>'
        b"<urlset><url><loc>&lol2;</loc></url></urlset>"
    )

    with pytest.raises(SitemapError, match="invalid sitemap XML"):
        read_sitemap(write(tmp_path, data))


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"<urlset><url>", "invalid sitemap XML"),
        (b"<rss><channel/></rss>", "not a sitemap"),
        (b"\x1f\x8bnot really gzip", "invalid gzip"),
    ],
)
def test_rejects_malformed_content(tmp_path: Path, data: bytes, message: str) -> None:
    with pytest.raises(SitemapError, match=message):
        read_sitemap(write(tmp_path, data))


def test_reports_http_errors() -> None:
    session = http_session({"https://a.example/s.xml": (404, b"")})

    with pytest.raises(SitemapError, match="HTTP 404"):
        read_sitemap("https://a.example/s.xml", session=session)


def test_reports_network_errors() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = requests.ConnectionError("down")

    with pytest.raises(SitemapError, match="could not be fetched"):
        read_sitemap("https://a.example/s.xml", session=session)


def test_reports_missing_files(tmp_path: Path) -> None:
    with pytest.raises(SitemapError, match="cannot read"):
        read_sitemap(tmp_path / "missing.xml")


def test_enforces_size_limits(tmp_path: Path) -> None:
    big = urlset(*(url(f"https://a.example/{i}") for i in range(50)))
    session = http_session({"https://a.example/s.xml": (200, big)})

    with patch("kliz.sitemap.MAX_SITEMAP_BYTES", 100):
        with pytest.raises(SitemapError, match="exceeds"):
            read_sitemap(write(tmp_path, big))
        with pytest.raises(SitemapError, match="exceeds"):
            read_sitemap(write(tmp_path, gzip.compress(big), "s.xml.gz"))
        with pytest.raises(SitemapError, match="exceeds"):
            read_sitemap("https://a.example/s.xml", session=session)


def test_owned_session_is_closed() -> None:
    session = http_session({"https://a.example/s.xml": (200, urlset())})

    with patch("kliz.sitemap.requests.Session", return_value=session):
        assert read_sitemap("https://a.example/s.xml") == []
    session.close.assert_called_once()


def test_rejects_invalid_timeout() -> None:
    with pytest.raises(ValueError, match="timeout"):
        read_sitemap("https://a.example/s.xml", timeout=0)
