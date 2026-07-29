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

```python
from kliz import BaseProvider


class CustomProvider(BaseProvider):
    def notify(self, url: str) -> bool:
        # Appel vers l'API du moteur concerné
        return True
```

## Configuration des fournisseurs

### IndexNow

La clé doit être publiée conformément aux règles d'IndexNow. Si
`key_location` est fourni, il est transmis dans le champ `keyLocation`.

```python
from kliz import IndexNowProvider

provider = IndexNowProvider(
    api_key="votre-cle-valide",
    key_location="https://example.com/votre-cle-valide.txt",  # optionnel
    timeout=10.0,
)
provider.notify("https://example.com/page")
```

Pour soumettre plusieurs URL du même hôte dans un seul appel :

```python
provider.notify_many(
    [
        "https://example.com/page-1",
        "https://example.com/page-2",
    ]
)
```

IndexNow accepte jusqu'à 10 000 URL par requête. `kliz` classe les erreurs
`429` et `5xx` comme retentables.

### Google

Activez l'API Google Indexing pour votre projet, créez un compte de service et
autorisez-le sur la propriété concernée. Ne versionnez jamais le fichier JSON
du compte de service.

> **Restriction importante :** l'API Google Indexing est officiellement
> réservée aux pages contenant un `JobPosting` ou un `BroadcastEvent` intégré
> dans un `VideoObject`. N'utilisez pas ce provider comme API d'indexation
> générique pour les autres contenus ; utilisez notamment un sitemap pour leur
> couverture.

```python
from kliz import GoogleProvider

provider = GoogleProvider(
    "/run/secrets/google-service-account.json",
    timeout=60.0,
    num_retries=2,
)
provider.notify("https://example.com/jobs/backend-python")
```

L'API Google Indexing est soumise aux règles d'éligibilité et aux quotas de
Google. Une notification ne garantit pas l'indexation de l'URL.

## Recettes / Intégration Asynchrone

`kliz` reste volontairement synchrone. Pour une exécution asynchrone, placez
l'appel dans un worker, une tâche ou un job appartenant à votre application.
Ainsi, les dépendances d'infrastructure ne contaminent pas le package.

### Tâche Celery (Python/Django)

Dans un projet Django utilisant déjà Celery, la tâche peut lire sa
configuration depuis les settings et laisser Celery gérer les retries :

```python
# myapp/tasks.py — ce code appartient à l'application, pas à kliz
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

Depuis une vue, un signal ou un service Django :

```python
from myapp.tasks import notify_search_engines

notify_search_engines.delay("https://example.com/articles/nouveau")
```

Pour isoler les retries et quotas de chaque moteur, utilisez idéalement une
tâche par provider. Le provider Google ne doit être ajouté que pour les pages
officiellement éligibles.

### Job générique

Le même principe fonctionne avec un scheduler, un worker maison, RQ, Dramatiq,
une fonction serverless ou un cron. Le job ne connaît que l'API publique de
`kliz` :

```python
from kliz import IndexNowProvider, Kliz


class ContentIndexingJob:
    def __init__(self, api_key: str) -> None:
        self.indexer = Kliz([IndexNowProvider(api_key=api_key)])
