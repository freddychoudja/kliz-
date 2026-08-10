# Changelog

Toutes les modifications notables de `kliz` sont documentées dans ce fichier.
Le projet suit le versionnage sémantique.

## [Unreleased]

### Ajouté

- Session HTTP `requests` réutilisable dans `IndexNowProvider`, avec injection
  d'une session externe et méthode `close()` pour libérer les connexions.
- Construction paresseuse du client Google Indexing : le fichier de compte de
  service n'est lu qu'au premier `notify` ; les erreurs de configuration sont
  non retentables et ne cassent plus le démarrage de l'application.

### Modifié

- Validation stricte des URL de notification : les fragments (`#`) sont
  toujours rejetés et les chaînes de requête (`?`) sont rejetées via le mode
  `require_clean` de `parse_http_url`.

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

