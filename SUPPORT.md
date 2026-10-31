# Getting help with kliz

🇫🇷 Questions in French are welcome too.

## Before you ask

1. Read the [documentation site](https://freddychoudja.github.io/kliz-/) and the
   [README](README.md). The FAQ answers the most common questions about indexing,
   key files and quotas.
2. Run the command again with `-vv` to see each HTTP request and response, and
   `--dry-run` to list the URLs without sending anything.
3. Search the [existing issues](https://github.com/freddychoudja/kliz-/issues?q=is%3Aissue),
   open and closed.

## Where to ask

| You want to… | Go to |
| :--- | :--- |
| Ask how to do something | [Open an issue](https://github.com/freddychoudja/kliz-/issues/new/choose) and pick **Question** |
| Report a bug | [Bug report](https://github.com/freddychoudja/kliz-/issues/new?template=bug_report.yml) |
| Suggest a feature or a new engine | [Feature request](https://github.com/freddychoudja/kliz-/issues/new?template=feature_request.yml) |
| Report a vulnerability | Privately, as described in [SECURITY.md](SECURITY.md) — never in a public issue |
| Report a conduct problem | Privately, as described in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |

## What to include

- The kliz version (`kliz --version`) and Python version.
- How you run it: command line, GitHub Action or Python library.
- The command or code, and the full output with `-vv`.

Remove API keys, service account content and private URLs before posting. kliz
already hides keys in its own logs, but your shell history and CI output may not.

## Response times

kliz is maintained by volunteers in their spare time. Most issues get a first
reply within a week. Pull requests that include tests are reviewed first.
