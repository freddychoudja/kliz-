# kliz

[![CI](https://github.com/freddychoudja/kliz-/actions/workflows/ci.yml/badge.svg)](https://github.com/freddychoudja/kliz-/actions/workflows/ci.yml)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kliz)](https://pypi.org/project/kliz/)
[![GitHub issues](https://img.shields.io/github/issues/freddychoudja/kliz-)](https://github.com/freddychoudja/kliz-/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`kliz` est un bot d'indexation SEO agnostique. Il permet à une application de
notifier plusieurs moteurs de recherche dès qu'une URL est créée ou mise à
jour.

Le package ne dépend ni de Django, ni de Celery, ni de Redis. Il expose une API
Python synchrone que l'application appelante peut exécuter directement ou
encapsuler dans le système de tâches de son choix.

## Installation

```bash
pip install kliz
```

Pour contribuer et exécuter les tests :

```bash
python -m pip install -e ".[dev]"
pytest --cov=kliz
```

## Démarrage rapide

```python
from kliz import GoogleProvider, IndexNowProvider, Kliz

indexer = Kliz(
    [
        IndexNowProvider(
            api_key="votre-cle-indexnow",
            key_location="https://example.com/votre-cle-indexnow.txt",
        ),
        GoogleProvider("/run/secrets/google-service-account.json"),
    ]
)

statuses = indexer.notify_all("https://example.com/articles/nouvel-article")
# {
#     "IndexNowProvider": True,
#     "GoogleProvider": True,
# }
```

`notify_all` continue d'appeler les autres fournisseurs lorsqu'un fournisseur
