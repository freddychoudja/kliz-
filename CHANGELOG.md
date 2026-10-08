# Changelog

All notable changes to `kliz` are documented in this file.
The project follows semantic versioning.

## [Unreleased]

## [0.3.1] - 2026-10-08

### Added

- "Signal" visual identity in `docs/brand/`: symbol, horizontal and stacked lockups
  (dark and light), GitHub avatar, social preview and usage guidelines. The README
  header switches lockup with GitHub's light or dark theme, and the docs site gets
  the new favicons and Apple touch icon.

### Changed

- Redesigned README: centered header with logo and badges, engine coverage table,
  `pipx` installation (fixes `externally-managed-environment` on recent Linux
  distributions), Action inputs and CLI options as tables, collapsible recipes.

## [0.3.0] - 2026-10-08

### Breaking changes

- The Google client libraries moved to the `google` extra: install
  `kliz[google]` to use `GoogleProvider` or `GoogleSearchConsoleProvider`.
  Without it, they raise `MissingDependencyError` (an `ImportError`) and the CLI
  exits with code `2`. A plain `pip install kliz` drops from about 144 MB and
  24 packages to about 4 MB and 7.
- Python 3.10 or newer is required (Python 3.9 reached end of life in October
  2025).

### Added

- `NotificationResult.urls`: the URLs each result covers.
- `BatchProvider.validate_url()`: per-URL validation hook used by the
  orchestrator.
- `kliz indexnow keygen` (`--write DIR`, `--site URL`) and
  `kliz indexnow verify-key`, backed by `IndexNowProvider.generate_key()`,
  `key_file_url()` and `verify_key()`. Verification detects missing files,
  redirects, wrong keys and HTML pages served with `200` for unknown paths.
- Sitemap reading: `read_sitemap()` and `kliz notify --sitemap` (URL or file,
  gzip, sitemap indexes, `--since` filtering on `<lastmod>`), with `defusedxml`
  parsing, 50 MB cap and clear errors for HTML pages served instead of a sitemap.
  New runtime dependency: `defusedxml`.
- `GoogleSearchConsoleProvider`: resubmits a sitemap through the Search Console
  API, the supported way to signal changes to Google for any page. CLI options
  `--gsc-site`, `--gsc-sitemap`, `--gsc-service-account-file` (`KLIZ_GSC_*`).
- GitHub Action (`action.yml`): notifies after each deployment from a sitemap
  or a URL list, verifies the IndexNow key first; exercised in CI by a dry run.
- Smarter retry: `Kliz` honors `Retry-After` (seconds or HTTP date), caps
  waits with `max_delay` (default 60 s), accepts a total `deadline` and an
  injectable `rng`. `ProviderError` and `NotificationResult` gain
  `retry_after`; results also report `attempts`. CLI `--max-attempts`
  (`KLIZ_MAX_ATTEMPTS`) and action input `max-attempts` (default 3).
- `kliz.normalize_url()`; providers submit normalized URLs (lowercase scheme
  and host, punycode for international domains, no default port, `/` for an
  empty path, percent-encoding of unsafe characters) and `notify_many`
  deduplicates on that form.
- `allow_query` on `IndexNowProvider`, `BatchProvider` and `GoogleProvider`
  to accept canonical URLs with a query string; CLI `--allow-query`
  (`KLIZ_ALLOW_QUERY`) and action input `allow-query`.
- Logging on the `kliz` logger hierarchy (silent by default through a
  `NullHandler`), `on_result` / `on_retry` hooks on `Kliz` with the new
  `RetryEvent`, and CLI `-v` / `-vv`. The GitHub Action logs at `INFO`. API
  keys are redacted as `<key>` in key file messages and never logged.
- CLI settings file: `kliz.toml` or `[tool.kliz]` in `pyproject.toml` (or
  `--config PATH`), below flags and `KLIZ_*` variables in precedence; a
  `sitemap` setting makes `kliz notify` work without arguments. New `tomli`
  dependency on Python 3.10 only.
- `kliz notify --json` report, URLs from stdin (`kliz notify -`,
  `--batch -`) and `--timeout` (`KLIZ_TIMEOUT`).
- `kliz notify --dry-run` lists the URLs without sending anything.

### Changed

- Package metadata and CLI help are in English; development status is Beta.
- `GoogleProvider` and `GoogleSearchConsoleProvider` share one client base.

- Retry jitter is proportional (up to 25 % of the delay) instead of a fixed
  0–0.25 s.

- Invalid provider settings in the CLI (such as a malformed IndexNow key) exit
  with code `2` and a clear message instead of an "unexpected error".

### Fixed

- Retry jitter came from a generator re-seeded with the clock on every wait;
  it now uses a real random generator.

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
[`CHANGELOG.fr.md`](CHANGELOG.fr.md).
