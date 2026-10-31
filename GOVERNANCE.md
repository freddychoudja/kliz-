# Governance

kliz is a small open-source project. This page says who decides what, and how
someone becomes one of the people who decide.

## Roles

**Contributors** are everyone who opens an issue, reviews a pull request, improves
the documentation or sends code. No permission is needed.

**Maintainers** review and merge pull requests, triage issues, and publish
releases. They are listed in [`.github/CODEOWNERS`](.github/CODEOWNERS).

The project is currently led by its author, Freddy Choudja, who has the final say
when maintainers disagree.

## How decisions are made

- Day-to-day changes are decided in the pull request: one maintainer approval and
  green CI are enough to merge.
- Changes to the public API, new runtime dependencies, new providers and anything
  that breaks compatibility start as an issue, so the design can be discussed
  before code is written.
- The project's constraints are written in [CONTRIBUTING.md](CONTRIBUTING.md): a
  framework-agnostic core, heavy SDKs in optional extras, mockable network calls
  and no committed secrets. Proposals that break them need a strong reason.

## Becoming a maintainer

Contributors who have made several substantial, well-reviewed contributions and
helped others in issues and reviews may be invited to become maintainers by the
existing maintainers. You can also ask.

## Releases

Releases follow [semantic versioning](https://semver.org/). Until 1.0, minor
versions may contain breaking changes; they are always listed under
**Breaking changes** in the [changelog](CHANGELOG.md). Releases are published to
PyPI from `vX.Y.Z` tags through Trusted Publishing.

## Changes to this document

Changes to governance are proposed as pull requests and stay open for at least a
week before they are merged.
