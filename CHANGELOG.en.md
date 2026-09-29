# Changelog

All notable changes to `kliz` are documented in this file.
The project follows semantic versioning.

## [Unreleased]

## [0.2.0] - 2026-09-29

### Added

- Opt-in retry on `Kliz` (`max_attempts`) with exponential backoff and jitter;
  injectable `sleep` and `clock`; off by default.
- Batch orchestration: `Kliz.notify_many` / `notify_many_detailed`, chunking by
  `max_urls_per_request` with a per-URL `notify` fallback.
- `BatchProvider` base and shared HTTP helpers (`_http.py`) to make new batch
  engines easier to add.
- Reusable `requests` HTTP session in `IndexNowProvider`, with external session
  injection and `close()`.
- Lazy construction of the Google Indexing client.
- CLI entry point `kliz` (`notify`, `providers`) configured via arguments or
  `KLIZ_*` environment variables.
- `BaseProvider.close()` hook and context-manager support on `Kliz`.

### Changed

- Strict validation of notification URLs (`require_clean`: reject `?` and `#`).
- `IndexNowProvider` now builds on `BatchProvider` and the shared HTTP helpers.

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
