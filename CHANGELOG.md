# Changelog

Toutes les modifications notables de `kliz` sont documentées dans ce fichier.
Le projet suit le versionnage sémantique.

## [Unreleased]

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

Une traduction anglaise de ce changelog est disponible dans
[`CHANGELOG.en.md`](CHANGELOG.en.md).
