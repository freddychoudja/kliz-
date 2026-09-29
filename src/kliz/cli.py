"""CLI entry point for kliz."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable

from kliz import Kliz, __version__
from kliz.exceptions import KlizError
from kliz.providers import GoogleProvider, IndexNowProvider


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
        help="Path to the Google service account JSON file",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_notify = sub.add_parser("notify", help="Notify providers of a URL")
    p_notify.add_argument("url", nargs="?", default=None, help="URL to notify")
    p_notify.add_argument(
        "--batch",
        default=None,
        help="File with one URL per line",
    )
    p_notify.set_defaults(command=_cmd_notify)
    p_providers = sub.add_parser("providers", help="List configured providers")
    p_providers.set_defaults(command=_cmd_providers)
    return parser


def _cmd_notify(args: argparse.Namespace) -> int:
    urls = _resolve_urls(args)
    indexer = _build_indexer(args)
    all_ok = True
    for url in urls:
        results = indexer.notify_all_detailed(url)
        failures = {
            name: result.error for name, result in results.items() if not result.success
        }
        if failures:
            all_ok = False
            for name, error in failures.items():
                print(
                    f"❌ {url} → {name}: {error}",
                    file=sys.stderr,
                )
        else:
            names = ", ".join(results)
            print(f"✅ {url} → {names}: OK")
    return 0 if all_ok else 1


def _cmd_providers(args: argparse.Namespace) -> int:
    indexer = _build_indexer(args)
    for provider in indexer.providers:
        kind = provider.__class__.__name__
        print(f"{kind} ({provider.name})")
    return 0


def _resolve_urls(args: argparse.Namespace) -> list[str]:
    if args.batch:
        return _read_urls_from_file(args.batch)
    if args.url:
        return [args.url]
    raise ConfigurationError("provide a URL or --batch <file>")


def _read_urls_from_file(path: str) -> list[str]:
    try:
        with open(path) as handle:
            urls = [
                line.strip()
                for line in handle
                if line.strip() and not line.startswith("#")
            ]
    except OSError as exc:
        raise ConfigurationError(f"cannot read {path}: {exc}") from exc
    if not urls:
        raise ConfigurationError(f"no URLs found in {path}")
    return urls


def _build_indexer(args: argparse.Namespace) -> Kliz:
    providers: list[IndexNowProvider | GoogleProvider] = []
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
    if not providers:
        raise ConfigurationError(
            "no providers configured: set --indexnow-api-key + "
            "--indexnow-key-location or --google-service-account-file "
            "(or the KLIZ_* env vars)",
        )
    return Kliz(providers)
