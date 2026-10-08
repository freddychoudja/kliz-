# Changelog

Toutes les modifications notables de `kliz` sont documentées dans ce fichier.
Le projet suit le versionnage sémantique.

## [Unreleased]

### Changements incompatibles

- Les bibliothèques Google passent dans l'extra `google` : installez
  `kliz[google]` pour utiliser `GoogleProvider` ou `GoogleSearchConsoleProvider`.
  Sans lui, ils lèvent `MissingDependencyError` (une `ImportError`) et la CLI
  termine avec le code `2`. Un simple `pip install kliz` passe d'environ 144 Mo
  et 24 paquets à environ 4 Mo et 7.
- Python 3.10 ou plus récent est requis (Python 3.9 est en fin de vie depuis
  octobre 2025).

### Ajouté

- `NotificationResult.urls` : les URL couvertes par chaque résultat.
- `BatchProvider.validate_url()` : point d’extension de validation par URL
  utilisé par l’orchestrateur.
- `kliz indexnow keygen` (`--write DIR`, `--site URL`) et
  `kliz indexnow verify-key`, appuyés sur `IndexNowProvider.generate_key()`,
  `key_file_url()` et `verify_key()`. La vérification détecte les fichiers
  absents, les redirections, les mauvaises clés et les pages HTML servies en
  `200` pour les chemins inconnus.
- Lecture de sitemaps : `read_sitemap()` et `kliz notify --sitemap` (URL ou
  fichier, gzip, index de sitemaps, filtre `--since` sur `<lastmod>`), analyse
  via `defusedxml`, plafond de 50 Mo et erreurs claires quand une page HTML est
  servie à la place du sitemap. Nouvelle dépendance : `defusedxml`.
- `GoogleSearchConsoleProvider` : soumet à nouveau un sitemap via l'API Search
  Console, la méthode prise en charge pour signaler des changements à Google
  pour toute page. Options CLI `--gsc-site`, `--gsc-sitemap`,
  `--gsc-service-account-file` (`KLIZ_GSC_*`).
- GitHub Action (`action.yml`) : notifie après chaque déploiement depuis un
  sitemap ou une liste d'URL, vérifie d'abord la clé IndexNow ; testée en CI
  par une exécution à blanc.
- Retry plus intelligent : `Kliz` respecte `Retry-After` (secondes ou date
  HTTP), plafonne les attentes avec `max_delay` (60 s par défaut), accepte un
  budget total `deadline` et un `rng` injectable. `ProviderError` et
  `NotificationResult` gagnent `retry_after` ; les résultats indiquent aussi
  `attempts`. Option CLI `--max-attempts` (`KLIZ_MAX_ATTEMPTS`) et entrée
  d'action `max-attempts` (3 par défaut).
- `kliz notify --dry-run` liste les URL sans rien envoyer.

### Modifié

- Métadonnées du paquet et aide de la CLI en anglais ; statut Beta.
- `GoogleProvider` et `GoogleSearchConsoleProvider` partagent une base commune.

- Le jitter du retry est proportionnel (jusqu'à 25 % du délai) au lieu d'un
  fixe de 0 à 0,25 s.

### Corrigé

- Le jitter du retry venait d'un générateur réensemencé avec l'horloge à chaque
  attente ; il utilise désormais un vrai générateur aléatoire.

- `Kliz.notify_many` regroupe les URL par hôte avant le découpage : mélanger
  `a.com` et `www.a.com` ne fait plus échouer tout le lot.
- Une URL invalide (chaîne de requête, schéma incorrect, hors du chemin de
  `key_location` IndexNow) est signalée comme un échec individuel au lieu de
  faire rejeter tout le lot.
- IndexNow ne vérifiait que la première URL d’un lot par rapport à
  `key_location` ; toutes les URL sont désormais vérifiées.
- `notify_many` supprime les espaces et les doublons.
- `kliz notify --batch` envoie de vrais lots (une requête par hôte et par
  tranche au lieu d’une par URL) et ignore les commentaires `#` indentés.

## [0.2.0] - 2026-09-29

### Ajouté

- Retry opt-in sur `Kliz` (`max_attempts`) avec backoff exponentiel et jitter ;
  `sleep` et `clock` injectables ; désactivé par défaut.
- Orchestration par lots : `Kliz.notify_many` / `notify_many_detailed`, avec
  découpage selon `max_urls_per_request` et repli en boucle `notify`.
- Base `BatchProvider` et helpers HTTP partagés (`_http.py`) pour faciliter
  l'ajout de nouveaux moteurs à lots.
- Session HTTP `requests` réutilisable dans `IndexNowProvider`, avec injection
  d'une session externe et méthode `close()`.
- Construction paresseuse du client Google Indexing.
- Point d'entrée CLI `kliz` (`notify`, `providers`) avec configuration via
  arguments ou variables d'environnement `KLIZ_*`.
- Hook `BaseProvider.close()` et gestionnaire de contexte sur `Kliz`.

### Modifié

- Validation stricte des URL de notification (`require_clean` : rejet de `?` et
  `#`).
- `IndexNowProvider` s'appuie sur `BatchProvider` et les helpers HTTP partagés.

## [0.1.0] - 2026-07-29

### Ajouté

- Architecture Adapter/Strategy avec `BaseProvider`.
- Provider IndexNow avec notification unitaire et par lots.
- Provider Google Indexing pour les pages officiellement éligibles.
- Orchestrateur `Kliz` avec résultats simples et détaillés.
- Erreurs structurées indiquant si une opération peut être retentée.
- Validation des URL, clés IndexNow, timeouts et chemins de clés.
- Tests unitaires mockés, contrôle de couverture, lint et typage strict.
- CI multi-version Python et publication PyPI via Trusted Publishing.

La version de référence, en anglais, est [`CHANGELOG.md`](CHANGELOG.md).
