<h1 align="center">
  <a href="https://github.com/freddychoudja/kliz-">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/freddychoudja/kliz-/main/docs/brand/lockup-horizontal-light.svg">
      <img src="https://raw.githubusercontent.com/freddychoudja/kliz-/main/docs/brand/lockup-horizontal-dark.svg" alt="kliz" width="270" height="90">
    </picture>
  </a>
</h1>

<h3 align="center">One publish. Every engine, notified.</h3>

<p align="center">
  Tell search engines about your new and updated pages, the moment you publish.
</p>

<p align="center">
  <a href="https://pypi.org/project/kliz/"><img src="https://img.shields.io/pypi/v/kliz?color=2FBF71&label=PyPI" alt="PyPI version"></a>
  <a href="https://pypi.org/project/kliz/"><img src="https://img.shields.io/pypi/pyversions/kliz?color=101820" alt="Python versions"></a>
  <a href="https://github.com/freddychoudja/kliz-/actions/workflows/ci.yml"><img src="https://github.com/freddychoudja/kliz-/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/freddychoudja/kliz-/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-FFB703" alt="MIT license"></a>
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#github-action">GitHub Action</a> ·
  <a href="#command-line">CLI</a> ·
  <a href="#python-api">Python API</a> ·
  <a href="https://freddychoudja.github.io/kliz-/">Docs</a> ·
  <a href="https://github.com/freddychoudja/kliz-/blob/main/README.fr.md">Français</a>
</p>

---

`kliz` notifies search engines as soon as a page is created or updated, from a single URL,
a list or a whole sitemap. It works as a **command-line tool**, a **GitHub Action** that runs
after every deployment, or a **Python library** with no framework attached.

- **One ping, many engines.** IndexNow reaches Bing, Yandex, Naver, Seznam and Yep at once;
  Search Console covers Google.
- **Sitemap-native.** Point it at `sitemap.xml` (indexes and `.gz` included) and optionally
  only send pages changed since a date.
- **Safe by default.** URLs are validated and normalized, one bad URL never sinks a batch,
  keys never reach the logs, XML is parsed defensively.
- **Reliable.** Opt-in retries honor `Retry-After`, with capped backoff and a time budget.
- **Light.** `pip install kliz` pulls 7 small packages; Google support is an optional extra.

## Search engine coverage

| Engine | How kliz reaches it | Provider |
| :--- | :--- | :--- |
| **Bing** (also powers Yahoo, DuckDuckGo, Ecosia, Copilot) | [IndexNow](https://www.indexnow.org/) | `IndexNowProvider` |
| **Yandex**, **Naver**, **Seznam**, **Yep** | IndexNow (shared with Bing) | `IndexNowProvider` |
| **Google**, any page | Sitemap resubmission through the Search Console API | `GoogleSearchConsoleProvider` |
| **Google**, job postings and livestreams only | Indexing API | `GoogleProvider` |

> **Note:** a notification asks an engine to crawl; it never guarantees indexing. Keep your sitemap
> accurate and its `<lastmod>` dates honest.

## Install

kliz needs Python 3.10 or newer.

```bash
pipx install kliz              # command-line use (recommended)
pip install kliz               # inside a virtual environment or project
uv tool install kliz           # with uv
```

Add Google support with the `google` extra: `pipx install 'kliz[google]'` or
`pip install 'kliz[google]'`.

> **Tip:** on Arch, Debian 12+, Ubuntu 23.04+ or Homebrew Python, a plain `pip install` outside a
> virtual environment fails with `externally-managed-environment`. Use `pipx`, which installs
> the `kliz` command in its own isolated environment.

## Quick start

**1. Create an IndexNow key** and publish its file with your site (here, a `public/` folder):

```bash
KEY=$(kliz indexnow keygen --write public/ --site https://example.com)
```

**2. Deploy, then check what search engines will see:**

```bash
kliz --indexnow-api-key "$KEY" indexnow verify-key --site https://example.com
# ✅ https://example.com/<key>.txt serves the IndexNow key
```

**3. Notify every page of your sitemap:**

```bash
export KLIZ_INDEXNOW_API_KEY="$KEY"
export KLIZ_INDEXNOW_KEY_LOCATION="https://example.com/$KEY.txt"
kliz notify --sitemap https://example.com/sitemap.xml
```

Then let the [GitHub Action](#github-action) do it after every deployment.

## GitHub Action

Add this workflow to your **site's** repository. It runs after each successful production
deployment (Vercel, Netlify, Cloudflare Pages and others send `deployment_status`), notifies
IndexNow engines and resubmits your sitemap to Google.

```yaml
# .github/workflows/indexing.yml
name: Search engine indexing
on:
  deployment_status:

jobs:
  index:
    if: >-
      github.event.deployment_status.state == 'success' &&
      github.event.deployment_status.environment == 'Production'
    runs-on: ubuntu-latest
    steps:
      - uses: freddychoudja/kliz-@v0.3.1
        with:
          sitemap: https://example.com/sitemap.xml
          indexnow-api-key: ${{ secrets.INDEXNOW_KEY }}
          indexnow-key-location: https://example.com/${{ secrets.INDEXNOW_KEY }}.txt
          gsc-site: https://example.com/
          gsc-service-account-json: ${{ secrets.GSC_SERVICE_ACCOUNT_JSON }}
```

| Input | Default | Description |
| :--- | :---: | :--- |
| `sitemap` | | Sitemap URL or workspace file to notify |
| `urls` | | URLs to notify, one per line (when `sitemap` is empty) |
| `since` | | Only sitemap pages whose `<lastmod>` is on or after this ISO date |
| `indexnow-api-key` | | IndexNow key, from a secret |
| `indexnow-key-location` | | URL of the published key file |
| `verify-key` | `true` | Check the key file before notifying |
| `gsc-site` | | Search Console property (`https://example.com/` or `sc-domain:example.com`) |
| `gsc-sitemap` | `sitemap` | Sitemap URL to resubmit to Search Console |
| `gsc-service-account-json` | | Service account JSON content, from a secret |
| `max-attempts` | `3` | Attempts per notification for temporary failures |
| `allow-query` | `false` | Accept URLs with a query string |
| `dry-run` | `false` | List the URLs without notifying |

Providers without credentials are skipped. The service account JSON is written to a private
temporary file deleted at the end of the step. Linux and macOS runners are supported.

## Command line

```bash
kliz notify https://example.com/page                      # one URL
kliz notify --batch urls.txt                              # one URL per line, # for comments
cat urls.txt | kliz notify -                              # from stdin (also --batch -)
kliz notify --sitemap https://example.com/sitemap.xml     # every page of a sitemap
kliz notify --sitemap sitemap.xml.gz --since 2026-10-01   # only recent changes
kliz notify --sitemap sitemap.xml --dry-run               # list, send nothing
kliz notify --sitemap sitemap.xml --json                  # machine-readable report
kliz providers                                            # list configured providers
kliz indexnow keygen --write public/ --site https://example.com   # create a key
kliz indexnow verify-key --site https://example.com              # check its file
```

| Option | Environment variable | Purpose |
| :--- | :--- | :--- |
| `--indexnow-api-key` | `KLIZ_INDEXNOW_API_KEY` | IndexNow key |
| `--indexnow-key-location` | `KLIZ_INDEXNOW_KEY_LOCATION` | URL of the key file |
| `--gsc-site` | `KLIZ_GSC_SITE` | Search Console property |
| `--gsc-service-account-file` | `KLIZ_GSC_SERVICE_ACCOUNT_FILE` | Service account JSON file |
| `--gsc-sitemap` | `KLIZ_GSC_SITEMAP` | Sitemap to resubmit (default: `--sitemap` URL, else `<property>/sitemap.xml`) |
| `--google-service-account-file` | `KLIZ_GOOGLE_SERVICE_ACCOUNT_FILE` | Indexing API (job postings and livestreams only) |
| `--max-attempts` | `KLIZ_MAX_ATTEMPTS` | Attempts for temporary failures (default `1`) |
| `--timeout` | `KLIZ_TIMEOUT` | Network timeout in seconds |
| `--allow-query` | `KLIZ_ALLOW_QUERY` | Accept URLs with a query string |
| `--config` | | Settings file (see below) |
| `-v`, `-vv` | | Log progress (`INFO`) or HTTP details (`DEBUG`) to stderr |

Exit codes: `0` success (or nothing changed), `1` a notification failed, `2` invalid
configuration.

### Settings file

Put recurring settings in `kliz.toml`, or under `[tool.kliz]` in `pyproject.toml`, where you
run `kliz` (or pass `--config PATH`). Keys are the long option names.

```toml
# kliz.toml
sitemap = "https://example.com/sitemap.xml"   # lets `kliz notify` run without arguments
indexnow-key-location = "https://example.com/your-key.txt"
gsc-site = "https://example.com/"
max-attempts = 3
timeout = 15
```

Precedence: command-line option, then `KLIZ_*` variable, then the file. Keep secrets in the
environment or a secrets manager, not in a committed file.

<details>
<summary><strong>JSON report format</strong></summary>

`--json` prints one document on stdout; the exit code is unchanged.

```json
{
  "ok": false,
  "dry_run": false,
  "urls": ["https://example.com/a"],
  "results": {
    "IndexNowProvider": [
      {
        "provider": "IndexNowProvider",
        "success": false,
        "retryable": true,
        "error": "IndexNowProvider rejected the notification with HTTP 429",
        "status_code": 429,
        "urls": ["https://example.com/a"],
        "retry_after": 30.0,
        "attempts": 3
      }
    ]
  }
}
```

</details>

## Python API

```python
from kliz import IndexNowProvider, Kliz, read_sitemap

indexer = Kliz(
    [
        IndexNowProvider(
            api_key="your-indexnow-key",
            key_location="https://example.com/your-indexnow-key.txt",
        ),
    ],
    max_attempts=3,
)

with indexer:
    indexer.notify_all("https://example.com/articles/new")      # {"IndexNowProvider": True}
    indexer.notify_many(read_sitemap("https://example.com/sitemap.xml"))
```

| Method | Returns |
| :--- | :--- |
| `notify_all(url)` | `{provider: bool}` |
| `notify_all_detailed(url)` | `{provider: NotificationResult}` |
| `notify_many(urls)` | `{provider: bool}`, true when every batch succeeded |
| `notify_many_detailed(urls)` | `{provider: [NotificationResult, ...]}`, one per batch or rejected URL |

A `NotificationResult` carries `success`, `urls`, `error`, `status_code`, `retryable`,
`retry_after` and `attempts`. `notify_all` keeps going when a provider fails; calling
`provider.notify(url)` directly raises `ProviderError` instead. If two providers share a
name, results are keyed `IndexNowProvider`, `IndexNowProvider#2`, and so on.

`notify_many` deduplicates URLs, groups them by host and splits them by each provider's
batch limit (10,000 for IndexNow). An invalid URL gets its own failed result instead of
failing the batch.

### Sitemaps

`read_sitemap(source, since=None, timeout=10.0)` reads a sitemap or sitemap index from a URL
or a file, compressed or not, and returns its page URLs (`<url><loc>`), ignoring image,
video and hreflang entries. With `since`, pages whose `<lastmod>` is older are skipped;
pages without `<lastmod>` are kept. XML goes through `defusedxml` with DTDs forbidden, and
each file is capped at 50 MB, as in the sitemap protocol.

### Retries

Retry is off by default (`max_attempts=1`). When enabled, temporary failures (HTTP 429, 5xx,
network errors) wait for the server's `Retry-After` if it sent one, otherwise for an
exponential backoff (1 s, 2 s, 4 s, plus up to 25 % jitter) capped by `max_delay`.

```python
Kliz(providers, max_attempts=3, max_delay=60.0, deadline=120.0)
```

If the server asks to wait longer than `max_delay`, or the next wait would overrun
`deadline`, kliz stops and returns the failure with `retryable=True`, `retry_after` and
`attempts`, so a task queue can reschedule it. The Google providers also retry internally
(`num_retries=2`); set `num_retries=0` to rely on kliz alone.

### URL rules

Every URL is checked before it is sent: `http` or `https` with a host, no credentials, no
fragment (`#...`), and no query string unless the provider has `allow_query=True` (for
canonical URLs such as WordPress's `/?p=123`).

Accepted URLs are normalized with `kliz.normalize_url()`: lowercase scheme and host,
international domains in ASCII form (`bücher.example` → `xn--bcher-kva.example`), default
ports and trailing host dots removed, an empty path turned into `/`, and characters not
allowed in a URL percent-encoded. Path case, existing escapes and parameter order are kept.

### Logging and metrics

kliz logs on the `kliz` logger and stays silent until your application configures logging:
successes and retries at `INFO`, failures and rejected URLs at `WARNING`, HTTP requests at
`DEBUG`. API keys are never logged; key file URLs show the key as `<key>`.

```python
from kliz import Kliz, NotificationResult, RetryEvent


def record(result: NotificationResult) -> None:
    metrics.increment(f"indexing.{result.provider}.{'ok' if result.success else 'failed'}")


def on_retry(event: RetryEvent) -> None:
    metrics.increment(f"indexing.{event.provider}.retry")


indexer = Kliz(providers, max_attempts=3, on_result=record, on_retry=on_retry)
```

`on_result` receives every final result, including URLs rejected before sending;
`on_retry` receives a `RetryEvent` (`provider`, `attempt`, `delay`, `error`, `urls`) before
each wait. An exception raised by a hook is logged and ignored.

## Providers

### IndexNow

```python
from kliz import IndexNowProvider

provider = IndexNowProvider(
    api_key="your-key",                                  # 8–128 letters, digits or dashes
    key_location="https://example.com/your-key.txt",     # optional, default <site>/<key>.txt
    timeout=10.0,
    allow_query=False,
)
provider.notify_many(["https://example.com/page-1", "https://example.com/page-2"])
provider.close()
```

The key file must be served as plain text at `key_location`, and submitted URLs must sit on
the same host, under the key file's directory. `IndexNowProvider.generate_key()` creates a
key and `provider.verify_key(site_url)` checks the published file without following
redirects. It reports missing files, redirects, wrong keys, and sites that answer `200` with
an HTML page for unknown paths, a common trap with single-page apps on Vercel or Netlify. The
provider keeps one `requests.Session` (inject your own with `session=`) and classifies `429`
and `5xx` responses as retryable.

### Google Search Console (any site)

Google has no general "index this URL" API. The supported way to signal changed pages is to
resubmit their sitemap, which `GoogleSearchConsoleProvider` does through the Search Console
API.

1. Verify your site in [Search Console](https://search.google.com/search-console).
2. In Google Cloud, enable the *Google Search Console API*, create a service account and
   download its JSON key.
3. In Search Console, open *Settings → Users and permissions* and add the service account's
   email as an **Owner** or **Full** user.

```python
from kliz import GoogleSearchConsoleProvider          # pip install 'kliz[google]'

provider = GoogleSearchConsoleProvider(
    "/run/secrets/search-console.json",
    site_url="https://example.com/",                  # or "sc-domain:example.com"
    sitemap_url="https://example.com/sitemap.xml",    # default: <property>/sitemap.xml
)
provider.notify_many(urls)   # checks the URLs belong to the property, submits once
```

URLs outside the property are rejected individually and never sent. An HTTP 403 means the
service account is not a user of the property.

### Google Indexing API (job postings and livestreams)

> **Warning:** Google reserves the Indexing API for pages with a `JobPosting` or a `BroadcastEvent`
> embedded in a `VideoObject`. For any other page, use `GoogleSearchConsoleProvider`.

```python
from kliz import GoogleProvider                       # pip install 'kliz[google]'

GoogleProvider("/run/secrets/google-service-account.json").notify(
    "https://example.com/jobs/backend-python"
)
```

Both Google providers read the service account file lazily, on the first notification;
configuration errors are reported as non-retryable and recover once the file is fixed. Do
not share one instance between threads.

### Your own provider

Inherit from `BaseProvider` and implement `notify`, or from `BatchProvider` for engines that
take batches of same-host URLs: validation, normalization and the shared HTTP session come
for free.

```python
from urllib.parse import SplitResult

from kliz import BatchProvider


class MyEngineProvider(BatchProvider):
    max_urls_per_request = 100

    def _notify_many(self, urls: list[str], parsed_urls: list[SplitResult]) -> bool:
        ...  # one HTTP call for the batch; raise ProviderError on failure
        return True
```

## Integrations

kliz is synchronous and framework-agnostic: run it directly, or wrap it in your task system.

<details>
<summary><strong>Celery task (Django)</strong></summary>

```python
# myapp/tasks.py — application code, not part of kliz
from dataclasses import asdict

from celery import shared_task
from django.conf import settings

from kliz import IndexNowProvider, Kliz


@shared_task(bind=True, max_retries=5)
def notify_search_engines(self, url: str) -> dict[str, dict[str, object]]:
    indexer = Kliz(
        [
            IndexNowProvider(
                api_key=settings.INDEXNOW_API_KEY,
                key_location=settings.INDEXNOW_KEY_LOCATION,
            ),
        ]
    )
    results = indexer.notify_all_detailed(url)
    retryable = [result for result in results.values() if result.retryable]

    if retryable:
        delay = max((r.retry_after or 0) for r in retryable)
        raise self.retry(
            exc=RuntimeError("temporary indexing provider failure"),
            countdown=max(delay, min(60 * (2**self.request.retries), 3600)),
        )

    return {name: asdict(result) for name, result in results.items()}
```

```python
notify_search_engines.delay("https://example.com/articles/new")
```

</details>

<details>
<summary><strong>Any job runner (RQ, Dramatiq, cron, serverless)</strong></summary>

```python
from kliz import IndexNowProvider, Kliz


class ContentIndexingJob:
    def __init__(self, api_key: str) -> None:
        self.indexer = Kliz([IndexNowProvider(api_key=api_key)])

    def run(self, payload: dict[str, str]) -> dict[str, bool]:
        return self.indexer.notify_all(payload["url"])
```

</details>

## Production checklist

- Inject keys from a secrets manager; never commit them or the service account file.
- Enable retries (`max_attempts`), and reschedule results with `retryable=True`.
- Send permanent failures to a dead-letter queue.
- Track success rate, HTTP codes and quotas per provider with `on_result`.
- Keep your sitemap and its `<lastmod>` dates accurate.

## Contributing

Contributions are welcome; see [CONTRIBUTING.md](https://github.com/freddychoudja/kliz-/blob/main/CONTRIBUTING.md).
Tests mock every network call, so no key or account is needed:

```bash
git clone https://github.com/freddychoudja/kliz-.git && cd kliz-
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff format --check src tests && ruff check src tests && mypy src && pytest --cov=kliz
```

Releases are published to PyPI from `vX.Y.Z` tags through Trusted Publishing. Report
vulnerabilities privately as described in
[SECURITY.md](https://github.com/freddychoudja/kliz-/blob/main/SECURITY.md).

## License

[MIT](https://github.com/freddychoudja/kliz-/blob/main/LICENSE) © 2026 Freddy Choudja
