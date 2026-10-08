# Changelog

All notable changes to `kliz` are documented in this file.
The project follows semantic versioning.

## [Unreleased]

### Added

- `NotificationResult.urls`: the URLs each result covers.
- `BatchProvider.validate_url()`: per-URL validation hook used by the
  orchestrator.
- `kliz indexnow keygen` (`--write DIR`, `--site URL`) and
  `kliz indexnow verify-key`, backed by `IndexNowProvider.generate_key()`,
  `key_file_url()` and `verify_key()`. Verification detects missing files,
  redirects, wrong keys and HTML pages served with `200` for unknown paths.

### Fixed

- `Kliz.notify_many` groups URLs by host before chunking: mixing `a.com` and
  `www.a.com` no longer fails the whole batch.
- An invalid URL (query string, bad scheme, outside the IndexNow
  `key_location` path) is now reported as its own failure instead of
  discarding the entire batch.
- IndexNow checked only the first URL of a batch against `key_location`; every
  URL is now checked.
- `notify_many` strips and deduplicates URLs.
- `kliz notify --batch` sends real batches (one request per host and chunk
  instead of one per URL) and ignores indented `#` comments.

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
