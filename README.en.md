# kliz

[![CI](https://github.com/freddychoudja/kliz-/actions/workflows/ci.yml/badge.svg)](https://github.com/freddychoudja/kliz-/actions/workflows/ci.yml)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kliz)](https://pypi.org/project/kliz/)
[![GitHub issues](https://img.shields.io/github/issues/freddychoudja/kliz-)](https://github.com/freddychoudja/kliz-/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`kliz` is an agnostic SEO indexing bot. It lets an application notify several
search engines as soon as a URL is created or updated.

The package depends neither on Django, nor Celery, nor Redis. It exposes a
synchronous Python API that the calling application can run directly or wrap
in whatever task system it chooses.

A French version of this document is available in
[`README.md`](README.md).

## Installation

```bash
pip install kliz
```

A static web documentation is available at
[`docs/index.html`](docs/index.html). It can also be published through GitHub
Pages with the provided workflow.

To contribute and run the tests:

```bash
python -m pip install -e ".[dev]"
pytest --cov=kliz
```

## Quick start

```python
from kliz import GoogleProvider, IndexNowProvider, Kliz

indexer = Kliz(
    [
        IndexNowProvider(
            api_key="your-indexnow-key",
            key_location="https://example.com/your-indexnow-key.txt",
        ),
        GoogleProvider("/run/secrets/google-service-account.json"),
    ]
)

statuses = indexer.notify_all("https://example.com/articles/new-article")
# {
#     "IndexNowProvider": True,
#     "GoogleProvider": True,
# }
```

`notify_all` keeps calling the other providers when one fails. That provider's
status is then `False`. A direct call to `provider.notify(url)` lets a
`ProviderError` bubble up instead, so the application can apply its own retry
policy.

To get the cause, the HTTP status and the retry hint:

```python
results = indexer.notify_all_detailed(
    "https://example.com/articles/new-article"
)

for name, result in results.items():
    print(name, result.success, result.retryable, result.error)
```

If multiple instances share the same name, their keys are suffixed:
`IndexNowProvider`, `IndexNowProvider#2`, etc.

## Agnostic architecture

`BaseProvider` defines a minimal strategy: `notify(url) -> bool`. Each adapter
translates this contract to the relevant remote API:

- `IndexNowProvider` sends an HTTP request to the IndexNow API;
- `GoogleProvider` publishes a `URL_UPDATED` notification through the Google
  Indexing API;
- `Kliz` orchestrates the strategies injected in its constructor.

This separation lets you add an engine without modifying the orchestrator and
leaves the application free to choose its web framework, its queue and its
retry policy.

A custom provider only needs to inherit from `BaseProvider`:

```python
from kliz import BaseProvider


class CustomProvider(BaseProvider):
    def notify(self, url: str) -> bool:
        # Call to the relevant engine API
        return True
```

## URL validation

Every URL submitted to a provider is checked before being sent:

- the scheme must be `http` or `https` and a host must be present;
- credentials (`https://user:pass@...`) are forbidden;
- fragments (`#...`) are always rejected: they are never transmitted to the
  server and therefore can never designate a distinct resource;
- query strings (`?...`) are rejected for notifications: only a clean
  canonical URL is submitted to the engines.

The shared `parse_http_url(url, require_clean=True)` function applies these
rules. `require_clean` defaults to `False` so existing usages keep working;
only notifications require a clean URL.

## Provider configuration

### IndexNow

The key must be published according to the IndexNow rules. If
`key_location` is provided, it is transmitted in the `keyLocation` field.

```python
from kliz import IndexNowProvider

provider = IndexNowProvider(
    api_key="your-valid-key",
    key_location="https://example.com/your-valid-key.txt",  # optional
    timeout=10.0,
)
provider.notify("https://example.com/page")
```

The provider reuses a persistent HTTP connection (`requests.Session`) between
notifications, instead of rebuilding a connection and a TLS handshake for every
call. You can inject your own session (tests, shared network configuration,
proxies):

```python
import requests

provider = IndexNowProvider(
    api_key="your-valid-key",
    session=requests.Session(),
)
```

The internal session keeps connections open; call `provider.close()` when your
application shuts down to release them cleanly.

To submit several URLs of the same host in a single call:

```python
provider.notify_many(
    [
        "https://example.com/page-1",
        "https://example.com/page-2",
    ]
)
```

IndexNow accepts up to 10,000 URLs per request. `kliz` classifies `429` and
`5xx` errors as retryable.

### Google

Enable the Google Indexing API for your project, create a service account and
authorize it on the property. Never version the service-account JSON file.

> **Important restriction:** the Google Indexing API is officially reserved for
> pages containing a `JobPosting` or a `BroadcastEvent` embedded in a
> `VideoObject`. Do not use this provider as a generic indexing API for other
> content; use a sitemap for their coverage.

```python
from kliz import GoogleProvider

provider = GoogleProvider(
    "/run/secrets/google-service-account.json",
    timeout=60.0,
    num_retries=2,
)
provider.notify("https://example.com/jobs/backend-python")
```

The Google Indexing API is subject to Google's eligibility rules and quotas. A
notification never guarantees that the URL will be indexed.

The Indexing client is built lazily: the service-account file is only read on
the first `notify` call, then reused for subsequent calls. Creating the
provider triggers no file read. Configuration errors (missing file, invalid
JSON) surface at notification time, are marked as non-retryable, and the
provider recovers as soon as the file is fixed.

## Recipes / Async integration

`kliz` deliberately stays synchronous. For asynchronous execution, place the
call in a worker, a task or a job owned by your application. This way
infrastructure dependencies never pollute the package.

### Celery task (Python/Django)

In a Django project already using Celery, the task can read its configuration
from the settings and let Celery handle retries:

```python
# myapp/tasks.py — this code belongs to the application, not to kliz
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
        raise self.retry(
            exc=RuntimeError("temporary indexing provider failure"),
            countdown=min(60 * (2**self.request.retries), 3600),
        )

    return {name: asdict(result) for name, result in results.items()}
```

From a view, a signal or a Django service:

```python
from myapp.tasks import notify_search_engines

notify_search_engines.delay("https://example.com/articles/new")
```

To isolate each engine's retries and quotas, ideally use one task per
provider. The Google provider must only be added for officially eligible pages.

### Generic job

The same principle works with a scheduler, a home-made worker, RQ, Dramatiq, a
serverless function or cron. The job only knows `kliz`'s public API:

```python
from kliz import IndexNowProvider, Kliz


class ContentIndexingJob:
    def __init__(self, api_key: str) -> None:
        self.indexer = Kliz([IndexNowProvider(api_key=api_key)])

    def run(self, payload: dict[str, str]) -> dict[str, bool]:
        return self.indexer.notify_all(payload["url"])


# The chosen job system serializes this payload and calls job.run(payload).
job = ContentIndexingJob(api_key="your-key")
result = job.run({"url": "https://example.com/updated-page"})
```

## Tests

The tests mock the `requests` calls and the Google client. They require no
network access, no IndexNow key and no Google service account.

The full local validation is:

```bash
ruff format --check src tests
ruff check src tests
mypy src
pytest --cov=kliz
python -m build
twine check --strict dist/*
pip-audit . --strict
```

## Production use

The package stores no secrets and imposes no task system. In the application
that uses it:

- inject keys through a secrets manager;
- apply a backoff with jitter to `retryable=True` results;
- place permanent failures in a dead-letter queue;
- measure latency, success rate, HTTP codes and quotas per provider;
- never share a single `GoogleProvider` instance between several threads;
- keep a sitemap up to date: a notification never guarantees indexing.

## Release

`vX.Y.Z` tags trigger the release workflow. The tag must match the version in
`pyproject.toml` exactly. Publishing uses PyPI Trusted Publishing and requires
no permanent PyPI token in GitHub.

Before the first release, configure a publisher on PyPI with the
`freddychoudja/kliz-` repository, the `release.yml` workflow and the `pypi`
environment.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) before
opening an issue or a pull request.

Source code and project tracking are available on
[GitHub](https://github.com/freddychoudja/kliz-).

## License

`kliz` is distributed under the [MIT license](LICENSE). Copyright © 2026 Freddy
Choudja.