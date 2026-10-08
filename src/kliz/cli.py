"""CLI entry point for kliz."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Callable

from kliz import Kliz, __version__
from kliz.exceptions import KlizError
from kliz.providers import (
    BaseProvider,
    GoogleProvider,
    GoogleSearchConsoleProvider,
    IndexNowProvider,
)
from kliz.sitemap import read_sitemap


class ConfigurationError(ValueError):
    """Raised when the CLI is misconfigured."""


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code: int = exc.code if isinstance(exc.code, int) else 0
        return code
    try:
        command: Callable[[argparse.Namespace], int] = args.command
        return command(args)
    except ConfigurationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KlizError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\naborted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"error: unexpected error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kliz",
        description=(
            "Bot d'indexation SEO agnostique pour notifier les moteurs de recherche."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "--indexnow-api-key",
        default=os.environ.get("KLIZ_INDEXNOW_API_KEY"),
        help="IndexNow API key (KLIZ_INDEXNOW_API_KEY env var)",
    )
    parser.add_argument(
        "--indexnow-key-location",
        default=os.environ.get("KLIZ_INDEXNOW_KEY_LOCATION"),
        help="URL where the IndexNow key file is hosted",
    )
    parser.add_argument(
        "--google-service-account-file",
        default=os.environ.get("KLIZ_GOOGLE_SERVICE_ACCOUNT_FILE"),
        help="Path to the Google service account JSON file (Indexing API: job"
        " posting and livestream pages only)",
    )
    parser.add_argument(
        "--gsc-site",
        default=os.environ.get("KLIZ_GSC_SITE"),
        help="Search Console property, e.g. https://example.com/ or"
        " sc-domain:example.com (KLIZ_GSC_SITE env var)",
    )
    parser.add_argument(
        "--gsc-sitemap",
        default=os.environ.get("KLIZ_GSC_SITEMAP"),
        help="Sitemap URL to resubmit to Search Console (default: the --sitemap"
        " URL, else <property>/sitemap.xml)",
    )
    parser.add_argument(
        "--gsc-service-account-file",
        default=os.environ.get("KLIZ_GSC_SERVICE_ACCOUNT_FILE"),
        help="Service account JSON file allowed on the Search Console property",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_notify = sub.add_parser("notify", help="Notify providers of a URL")
    p_notify.add_argument("url", nargs="?", default=None, help="URL to notify")
    p_notify.add_argument(
        "--batch",
        default=None,
        help="File with one URL per line",
    )
    p_notify.add_argument(
        "--sitemap",
        default=None,
        help="Sitemap or sitemap index (URL or file, .xml or .xml.gz)",
    )
    p_notify.add_argument(
        "--since",
        default=None,
        help="With --sitemap: only URLs whose <lastmod> is on or after this"
        " ISO date or datetime (e.g. 2026-10-01)",
    )
    p_notify.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the URLs that would be notified and send nothing",
    )
    p_notify.set_defaults(command=_cmd_notify)
    p_providers = sub.add_parser("providers", help="List configured providers")
    p_providers.set_defaults(command=_cmd_providers)

    p_indexnow = sub.add_parser("indexnow", help="Manage the IndexNow key")
    indexnow_sub = p_indexnow.add_subparsers(dest="indexnow_command", required=True)
    p_keygen = indexnow_sub.add_parser(
        "keygen",
        help="Generate a key and print it (only the key goes to stdout)",
    )
    p_keygen.add_argument(
        "--length", type=int, default=32, help="Key length, 8 to 128 (default 32)"
    )
    p_keygen.add_argument(
        "--write",
        metavar="DIR",
        default=None,
        help="Also write <key>.txt into DIR (e.g. your site's public/ folder)",
    )
    p_keygen.add_argument(
        "--site",
        default=None,
        help="Site URL, to print where the key file must be served",
    )
    p_keygen.set_defaults(command=_cmd_indexnow_keygen)
    p_verify = indexnow_sub.add_parser(
        "verify-key",
        help="Check that the key file is served correctly",
    )
    p_verify.add_argument(
        "--site",
        default=None,
        help="Site URL; the key is looked up at <site>/<key>.txt unless"
        " --indexnow-key-location is set",
    )
    p_verify.set_defaults(command=_cmd_indexnow_verify_key)
    return parser


def _cmd_notify(args: argparse.Namespace) -> int:
    urls = _resolve_urls(args)
    if not urls:
        print(f"nothing changed since {args.since}, nothing to notify", file=sys.stderr)
        return 0
    if args.dry_run:
        for url in urls:
            print(url)
        print(f"{len(urls)} URL(s), nothing sent (dry run)", file=sys.stderr)
        return 0
    indexer = _build_indexer(args)
    all_ok = True
    for name, results in indexer.notify_many_detailed(urls).items():
        for result in results:
            all_ok = all_ok and result.success
            for url in result.urls:
                if result.success:
                    print(f"✅ {url} → {name}: OK")
                else:
                    print(f"❌ {url} → {name}: {result.error}", file=sys.stderr)
    return 0 if all_ok else 1


def _cmd_providers(args: argparse.Namespace) -> int:
    indexer = _build_indexer(args)
    for provider in indexer.providers:
        kind = provider.__class__.__name__
        print(f"{kind} ({provider.name})")
    return 0


def _cmd_indexnow_keygen(args: argparse.Namespace) -> int:
    try:
        key = IndexNowProvider.generate_key(args.length)
        site_key_url = (
            IndexNowProvider(api_key=key).key_file_url(args.site) if args.site else None
        )
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc

    if args.write:
        path = os.path.join(args.write, f"{key}.txt")
        try:
            with open(path, "x", encoding="utf-8") as handle:
                handle.write(key)
        except OSError as exc:
            raise ConfigurationError(f"cannot write {path}: {exc}") from exc
        print(f"wrote {path}", file=sys.stderr)

    print(key)
    if site_key_url:
        print(
            f"serve the key file at {site_key_url}, then run:\n"
            f"  export KLIZ_INDEXNOW_API_KEY={key}\n"
            f"  export KLIZ_INDEXNOW_KEY_LOCATION={site_key_url}\n"
            "  kliz indexnow verify-key",
            file=sys.stderr,
        )
    return 0


def _cmd_indexnow_verify_key(args: argparse.Namespace) -> int:
    if not args.indexnow_api_key:
        raise ConfigurationError(
            "--indexnow-api-key (or KLIZ_INDEXNOW_API_KEY) is required"
        )
    if not args.indexnow_key_location and not args.site:
        raise ConfigurationError("provide --site or --indexnow-key-location")
    try:
        provider = IndexNowProvider(
            api_key=args.indexnow_api_key,
            key_location=args.indexnow_key_location,
        )
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc

    try:
        location = provider.verify_key(args.site)
    finally:
        provider.close()
    print(f"✅ {location} serves the IndexNow key")
    return 0


def _resolve_urls(args: argparse.Namespace) -> list[str]:
    sitemap = getattr(args, "sitemap", None)
    since = getattr(args, "since", None)
    sources = [bool(args.url), bool(args.batch), bool(sitemap)]
    if sum(sources) > 1:
        raise ConfigurationError("provide only one of a URL, --batch or --sitemap")
    if since and not sitemap:
        raise ConfigurationError("--since requires --sitemap")
    if sitemap:
        urls = read_sitemap(sitemap, since=_parse_since(since) if since else None)
        if not urls and not since:
            raise ConfigurationError(f"no URLs found in {sitemap}")
        return urls
    if args.batch:
        return _read_urls_from_file(args.batch)
    if args.url:
        return [args.url]
    raise ConfigurationError("provide a URL, --batch <file> or --sitemap <url>")


def _parse_since(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ConfigurationError(
            f"--since must be an ISO date or datetime, got {value!r}"
        ) from exc


def _read_urls_from_file(path: str) -> list[str]:
    try:
        with open(path) as handle:
            lines = (line.strip() for line in handle)
            urls = [line for line in lines if line and not line.startswith("#")]
    except OSError as exc:
        raise ConfigurationError(f"cannot read {path}: {exc}") from exc
    if not urls:
        raise ConfigurationError(f"no URLs found in {path}")
    return urls


def _build_indexer(args: argparse.Namespace) -> Kliz:
    providers: list[BaseProvider] = []
    if args.indexnow_api_key:
        if not args.indexnow_key_location:
            raise ConfigurationError(
                "--indexnow-key-location is required when --indexnow-api-key is set",
            )
        providers.append(
            IndexNowProvider(
                api_key=args.indexnow_api_key,
                key_location=args.indexnow_key_location,
            ),
        )
    if args.google_service_account_file:
        if not os.path.exists(args.google_service_account_file):
            raise ConfigurationError(
                f"service account file not found: {args.google_service_account_file}",
            )
        providers.append(
            GoogleProvider(args.google_service_account_file),
        )
    if args.gsc_site:
        providers.append(_build_search_console(args))
    if not providers:
        raise ConfigurationError(
            "no providers configured: set --indexnow-api-key + "
            "--indexnow-key-location, --gsc-site + --gsc-service-account-file "
            "or --google-service-account-file (or the KLIZ_* env vars)",
        )
    return Kliz(providers)


def _build_search_console(args: argparse.Namespace) -> GoogleSearchConsoleProvider:
    account_file = args.gsc_service_account_file
    if not account_file:
        raise ConfigurationError(
            "--gsc-service-account-file is required when --gsc-site is set"
        )
    if not os.path.exists(account_file):
        raise ConfigurationError(f"service account file not found: {account_file}")
    sitemap_url = args.gsc_sitemap
    sitemap = getattr(args, "sitemap", None)
    if not sitemap_url and sitemap and sitemap.lower().startswith("http"):
        sitemap_url = sitemap
    try:
        return GoogleSearchConsoleProvider(account_file, args.gsc_site, sitemap_url)
    except ValueError as exc:
        raise ConfigurationError(f"Search Console: {exc}") from exc
