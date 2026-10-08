# kliz

[![CI](https://github.com/freddychoudja/kliz-/actions/workflows/ci.yml/badge.svg)](https://github.com/freddychoudja/kliz-/actions/workflows/ci.yml)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kliz)](https://pypi.org/project/kliz/)
[![GitHub issues](https://img.shields.io/github/issues/freddychoudja/kliz-)](https://github.com/freddychoudja/kliz-/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Signalez vos pages nouvelles et modifiées aux moteurs de recherche, dès leur publication.**

`kliz` notifie Bing, Yandex, Naver, Seznam et Yep via
[IndexNow](https://www.indexnow.org/), et Google via Search Console, à partir
d'une URL, d'une liste ou d'un sitemap entier. Utilisable comme bibliothèque
Python, CLI ou GitHub Action exécutée après chaque déploiement.

```bash
pip install kliz
kliz indexnow keygen --write public/ --site https://example.com   # une fois
kliz notify --sitemap https://example.com/sitemap.xml             # à chaque déploiement (variables KLIZ_*)
```

Le package ne dépend ni de Django, ni de Celery, ni de Redis. Il expose une API
Python synchrone que l'application appelante peut exécuter directement ou
encapsuler dans le système de tâches de son choix.

## Installation

```bash
pip install kliz            # IndexNow, sitemaps, CLI (~4 Mo, 7 paquets)
pip install 'kliz[google]'  # + providers Google Search Console et Indexing API
```

Une documentation web statique est disponible dans
[`docs/index.html`](docs/index.html). Elle peut aussi être publiée via GitHub
Pages avec le workflow fourni.

🇬🇧 La version de référence, en anglais, est [`README.md`](README.md).

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

Pour soumettre plusieurs URL d'un coup, `notify_many` découpe selon
`max_urls_per_request` (lots IndexNow) et retombe sur une boucle `notify` pour
les autres providers :

```python
statuses = indexer.notify_many(
    [
        "https://example.com/articles/a",
        "https://example.com/articles/b",
    ]
)
```

Les URL sont dédoublonnées et regroupées par hôte. Une URL invalide obtient son
propre résultat d'échec au lieu de faire échouer tout le lot ;
`notify_many_detailed` renvoie, par provider, une liste de `NotificationResult`
dont le champ `urls` indique les URL couvertes par chaque résultat.

Le retry intégré est **désactivé par défaut** (`max_attempts=1`). Pour l'activer
avec backoff exponentiel et jitter :

```python
indexer = Kliz(
    [IndexNowProvider(api_key="votre-cle-indexnow")],
    max_attempts=3,
)
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

Pour un moteur qui accepte des lots d'URL sur le même hôte, héritez de
`BatchProvider` : `notify` et la validation (hôte commun, taille max, URL
propres) sont fournis ; il reste à implémenter `_notify_many`.

```python
from urllib.parse import SplitResult

from kliz import BatchProvider


class CustomBatchProvider(BatchProvider):
    max_urls_per_request = 100

    def _notify_many(
        self, urls: list[str], parsed_urls: list[SplitResult]
    ) -> bool:
        # Appel HTTP groupé vers le moteur
        return True
```

## Validation des URL

Toutes les URL soumises à un provider sont contrôlées avant tout envoi :

- le schéma doit être `http` ou `https` et l'hôte doit être présent ;
- les identifiants (`https://user:pass@...`) sont interdits ;
- les fragments (`#...`) sont toujours rejetés : ils ne sont jamais transmis au
  serveur et ne peuvent donc désigner un contenu distinct ;
- les chaînes de requête (`?...`) sont rejetées pour les notifications : seule
  une URL canonique propre est soumise aux moteurs.

La fonction partagée `parse_http_url(url, require_clean=True)` applique ces
règles. `require_clean` vaut `False` par défaut afin de ne pas casser les
usages existants ; seules les notifications exigent une URL propre.

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

Le provider réutilise une connexion HTTP persistante (`requests.Session`) entre
les notifications, afin de ne pas reconstruire une connexion et une poignée de
main TLS à chaque appel. Vous pouvez injecter votre propre session (tests,
configuration réseau partagée, proxies) :

```python
import requests

provider = IndexNowProvider(
    api_key="votre-cle-valide",
    session=requests.Session(),
)
```

La session interne garde les connexions ouvertes ; appelez `provider.close()` à
l'arrêt de votre application pour les libérer proprement.

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

Le client Indexing est construit de manière paresseuse : le fichier de compte
de service n'est lu qu'au premier appel de `notify`, puis réutilisé pour les
appels suivants. La création du provider ne déclenche donc aucune lecture de
fichier. Les erreurs de configuration (fichier absent, JSON invalide)
remontent au moment de la notification, sont marquées comme non retentables, et
le provider se rétablit dès que le fichier est corrigé.

### Google Search Console (tous les sites)

Google ne propose pas d'API générale « indexe cette URL ». La méthode prise en
charge pour signaler des pages modifiées est de soumettre à nouveau leur
sitemap, ce que fait `GoogleSearchConsoleProvider` via l'API Search Console.
Elle fonctionne pour tout type de page, contrairement à l'API Indexing
ci-dessus.

1. Validez le site dans [Search Console](https://search.google.com/search-console).
2. Dans Google Cloud, activez la *Google Search Console API*, créez un compte de
   service et téléchargez sa clé JSON.
3. Dans Search Console, *Paramètres → Utilisateurs et autorisations*, ajoutez
   l'e-mail du compte de service comme **Propriétaire** ou utilisateur **total**.

```python
from kliz import GoogleSearchConsoleProvider

provider = GoogleSearchConsoleProvider(
    "/run/secrets/search-console.json",
    site_url="https://example.com/",  # ou "sc-domain:example.com"
    sitemap_url="https://example.com/sitemap.xml",  # défaut : <propriété>/sitemap.xml
)
provider.notify_many(urls)  # vérifie que les URL appartiennent à la propriété, soumet une fois
```

Les URL hors de la propriété sont rejetées individuellement ; elles ne sont
jamais envoyées. Une nouvelle soumission demande à Google de relire le sitemap,
sans garantir l'indexation. Un HTTP 403 signifie que le compte de service n'est
pas utilisateur de la propriété.

### GitHub Action

Le dépôt est aussi une GitHub Action : après chaque déploiement en production,
elle notifie les moteurs IndexNow et soumet à nouveau le sitemap à Google
Search Console.

```yaml
# .github/workflows/indexing.yml dans le dépôt de votre site
name: Search engine indexing
on:
  deployment_status:   # envoyé par Vercel, Netlify, Cloudflare Pages... après un déploiement

jobs:
  index:
    if: >-
      github.event.deployment_status.state == 'success' &&
      github.event.deployment_status.environment == 'Production'
    runs-on: ubuntu-latest
    steps:
      - uses: freddychoudja/kliz-@main   # épinglez un tag de version ou un SHA
        with:
          sitemap: https://example.com/sitemap.xml
          indexnow-api-key: ${{ secrets.INDEXNOW_KEY }}
          indexnow-key-location: https://example.com/${{ secrets.INDEXNOW_KEY }}.txt
          gsc-site: https://example.com/
          gsc-service-account-json: ${{ secrets.GSC_SERVICE_ACCOUNT_JSON }}
```

Entrées : `sitemap` (URL ou fichier du dépôt) ou `urls` (une par ligne),
`since`, `indexnow-api-key`, `indexnow-key-location`, `verify-key` (`true` par
défaut : vérifie le fichier clé avant de notifier), `gsc-site`, `gsc-sitemap`,
`gsc-service-account-json` (le contenu JSON, depuis un secret ; écrit dans un
fichier temporaire privé supprimé à la fin), `dry-run`. Les providers sans
identifiants sont ignorés. Runners Linux et macOS pris en charge.

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

    def run(self, payload: dict[str, str]) -> dict[str, bool]:
        return self.indexer.notify_all(payload["url"])


# Le système de jobs choisi sérialise ce payload et appelle job.run(payload).
job = ContentIndexingJob(api_key="votre-cle")
result = job.run({"url": "https://example.com/page-modifiee"})
```

## Interface en ligne de commande

L'installation fournit aussi une commande `kliz` :

```bash
export KLIZ_INDEXNOW_API_KEY="votre-cle"
export KLIZ_INDEXNOW_KEY_LOCATION="https://example.com/votre-cle.txt"

kliz notify https://example.com/page  # une URL
kliz notify --batch urls.txt          # une URL par ligne, `#` pour un commentaire
kliz notify --sitemap https://example.com/sitemap.xml   # toutes les pages d'un sitemap
kliz notify --sitemap https://example.com/sitemap.xml --since 2026-10-01
kliz notify --sitemap sitemap.xml --dry-run             # lister sans rien envoyer
kliz providers                        # liste des providers configurés
kliz --version
```

Les crédits se passent aussi en options (`--indexnow-api-key`,
`--indexnow-key-location`, `--google-service-account-file`). Pour Search
Console, renseignez `--gsc-site` et `--gsc-service-account-file`
(`KLIZ_GSC_SITE`, `KLIZ_GSC_SERVICE_ACCOUNT_FILE`) ; le sitemap soumis est
`--gsc-sitemap`, sinon l'URL de `--sitemap`, sinon `<propriété>/sitemap.xml`. Le processus
termine avec le code `0` si tout a réussi, `1` en cas d'échec de notification
et `2` en cas de configuration invalide.

### Sitemaps

`--sitemap` (ou `read_sitemap()` en Python) lit un sitemap ou un index de
sitemaps, depuis une URL ou un fichier local, compressé ou non. Seules les URL de
pages (`<url><loc>`) sont retenues : les entrées image, vidéo et hreflang sont
ignorées. Avec `--since`, seules les pages dont le `<lastmod>` est postérieur ou
égal à la date sont notifiées (les pages sans `<lastmod>` sont conservées) ;
s'il n'y a rien de nouveau, la commande réussit sans rien envoyer, ce qui
convient à un pipeline de déploiement. Le XML est analysé avec `defusedxml`
(DTD interdites) et chaque fichier est limité à 50 Mo, comme le prévoit le
protocole sitemap.

```python
from datetime import date

from kliz import IndexNowProvider, Kliz, read_sitemap

urls = read_sitemap("https://example.com/sitemap.xml", since=date(2026, 10, 1))
if urls:
    Kliz([IndexNowProvider(api_key="votre-cle")]).notify_many(urls)
```

### Mettre en place la clé IndexNow

```bash
# Générer une clé et déposer <clé>.txt dans le dossier servi par votre site
KEY=$(kliz indexnow keygen --write public/ --site https://example.com)
# ...déployer le site, puis vérifier ce que les moteurs verront réellement :
kliz --indexnow-api-key "$KEY" indexnow verify-key --site https://example.com
```

`keygen` n'écrit que la clé sur la sortie standard, pour pouvoir la capturer
dans une variable ; les étapes suivantes vont sur la sortie d'erreur.
`verify-key` télécharge le fichier clé (`--indexnow-key-location`, ou
`<site>/<clé>.txt` par défaut) sans suivre les redirections et échoue avec un
message explicite si le fichier est absent, redirige, contient une autre clé, ou
si le site répond `200` avec une page HTML pour les chemins inconnus (piège
fréquent des applications monopage sur Vercel ou Netlify). Les mêmes
vérifications existent en Python via `IndexNowProvider.generate_key()` et
`provider.verify_key(site_url)`.

## Tests

Les tests mockent les appels `requests` et le client Google. Ils ne nécessitent
donc ni accès réseau, ni clé IndexNow, ni compte de service Google.

La validation complète locale est :

```bash
ruff format --check src tests
ruff check src tests
mypy src
pytest --cov=kliz
python -m build
twine check --strict dist/*
pip-audit . --strict
```

## Exploitation en production

Le package ne stocke aucun secret et n'impose aucun système de tâches. Dans
l'application qui l'utilise :

- injectez les clés par un gestionnaire de secrets ;
- activez le retry opt-in de `Kliz` (`max_attempts`) ou appliquez un backoff
  applicatif aux résultats `retryable=True` ;
- placez les échecs définitifs dans une dead-letter queue ;
- mesurez latence, taux de succès, codes HTTP et quotas par provider ;
- ne partagez pas une même instance `GoogleProvider` entre plusieurs threads ;
- conservez un sitemap à jour : une notification ne garantit jamais
  l'indexation.

## Publication

Les tags `vX.Y.Z` déclenchent le workflow de release. Le tag doit correspondre
exactement à la version de `pyproject.toml`. La publication utilise le Trusted
Publishing PyPI et ne nécessite aucun token PyPI permanent dans GitHub.

Avant la première release, configurez sur PyPI un publisher avec le dépôt
`freddychoudja/kliz-`, le workflow `release.yml` et l'environnement `pypi`.

## Contribuer

Les contributions sont les bienvenues. Consultez
[CONTRIBUTING.fr.md](CONTRIBUTING.fr.md) avant d'ouvrir une issue ou une pull
request.

Le code source et le suivi du projet sont disponibles sur
[GitHub](https://github.com/freddychoudja/kliz-).

## Licence

`kliz` est distribué sous la [licence MIT](LICENSE). Copyright © 2026 Freddy
Choudja.
