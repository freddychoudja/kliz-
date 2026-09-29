# Changelog

All notable changes to `kliz` are documented in this file.
The project follows semantic versioning.

## [Unreleased]

### Added

- Reusable `requests` HTTP session in `IndexNowProvider`, with injection of an
  external session and a `close()` method to release connections.
- Lazy construction of the Google Indexing client: the service-account file is
  only read on the first `notify`; configuration errors are non-retryable and
  no longer break application startup.
- `Kliz`: opt-in `max_attempts` parameter with exponential backoff and jitter;
  injectable `clock` and `sleep`. Retry is disabled by default.
- CLI entry point `kliz`: subcommands `notify` (single URL or `--batch`),
  `providers`, with credentials via arguments or `KLIZ_*` env vars.
- Batch notifications in `Kliz`: `notify_many` and `notify_many_detailed` with
  automatic chunking by `max_urls_per_request` and fallback loop for providers
  without native batch support.
- `BaseProvider.close()` hook and context manager support (`__enter__`/`__exit__`)
  on `Kliz`.

### Changed

- Strict validation of notification URLs: fragments (`#`) are always rejected
  and query strings (`?`) are rejected via the `require_clean` mode of
  `parse_http_url`.

## [0.1.0] - 2026-07-29

### Added

- Adapter/strategy architecture with `BaseProvider`.
- IndexNow provider with single and batch notification.
- Google Indexing provider for officially eligible pages.
- `Kliz` orchestrator with simple and detailed results.
- Structured errors indicating whether an operation can be retried.
- Validation of URLs, IndexNow keys, timeouts and key paths.
- Mocked unit tests, coverage control, linting and strict typing.
- Multi-version Python CI and PyPI publishing via Trusted Publishing.

A French version of this changelog is available in
[`CHANGELOG.md`](CHANGELOG.md).