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
échoue. Son statut vaut alors `False`. Un appel direct à `provider.notify(url)`
laisse en revanche remonter une `ProviderError` afin que l'application puisse
appliquer sa propre politique de retry.

Pour obtenir la cause, le statut HTTP et l'indication de retry :

```python
results = indexer.notify_all_detailed(
    "https://example.com/articles/nouvel-article"
)

for name, result in results.items():
    print(name, result.success, result.retryable, result.error)
```

Si plusieurs instances ont le même nom, leurs clés sont suffixées :
`IndexNowProvider`, `IndexNowProvider#2`, etc.

## Architecture agnostique

`BaseProvider` définit une stratégie minimale : `notify(url) -> bool`. Chaque
adaptateur traduit ce contrat vers l'API distante concernée :

- `IndexNowProvider` envoie une requête HTTP à l'API IndexNow ;
- `GoogleProvider` publie une notification `URL_UPDATED` via l'API Google
  Indexing ;
- `Kliz` orchestre les stratégies injectées dans son constructeur.

Cette séparation permet d'ajouter un moteur sans modifier l'orchestrateur et
laisse l'application libre de choisir son framework web, sa file d'attente et
sa politique de retry.

Un fournisseur personnalisé doit uniquement hériter de `BaseProvider` :

