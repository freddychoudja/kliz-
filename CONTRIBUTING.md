# Contributing to kliz

Thanks for contributing to `kliz`! The project aims to keep a light,
framework-agnostic core that is easy to integrate.

🇫🇷 A French version of this guide is available in
[`CONTRIBUTING.fr.md`](CONTRIBUTING.fr.md).

## Architecture principles

Every contribution must preserve these constraints:

- no dependency on Django, Celery, Redis or any other application framework in
  `src/kliz`;
- search engines are integrated as providers inheriting from `BaseProvider`;
- heavy SDKs go in an optional extra (like `kliz[google]`) and are imported
  lazily, raising `MissingDependencyError` when missing;
- network calls must have a timeout and stay mockable;
- no secret, token or service account file may ever be committed.

## Setting up

```bash
git clone https://github.com/freddychoudja/kliz-.git
cd kliz-
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff format --check src tests
ruff check src tests
mypy src
pytest --cov=kliz
```

## Proposing a change

1. Open an issue first for significant changes.
2. Create a dedicated branch from `main`.
3. Add or adapt the tests.
4. Make sure `pytest` passes without access to real APIs.
5. Open a pull request describing the problem and the solution.

Keep changes focused: a pull request must not contain refactoring unrelated to
its goal.

## Adding a provider

A new provider must:

1. inherit from `kliz.BaseProvider`, or from `kliz.BatchProvider` when the
   engine accepts batches of same-host URLs (implement `_notify_many`, and
   override `validate_url` for per-URL rules);
2. implement `notify(self, url: str) -> bool`;
3. return `True` after a successful notification;
4. raise `ProviderError` (with `retryable` and `status_code`) when the remote
   API fails;
5. be covered by tests that use mocks.

## Preparing a release

1. Update the version in `pyproject.toml`.
2. Move the `Unreleased` entries to that version in `CHANGELOG.md` and its
   translation `CHANGELOG.fr.md`.
3. Check tests, quality, audit and distributions locally.
4. Merge into `main` once CI passes.
5. Create and push a `vX.Y.Z` tag matching the version exactly.

The `release.yml` workflow builds the distributions and publishes them with
PyPI Trusted Publishing. Never add a permanent PyPI token to the GitHub
secrets.

## Reporting a vulnerability

Do not open a public issue for a vulnerability. Use the private channel
described in [SECURITY.md](SECURITY.md).
