# TODO — Feuille de route du projet `kliz`

> **Statut global :** 🟢 6 phases terminées sur 7 · la dernière phase (publication) reste à exécuter.

---

## **Légende**

| Symbole | Signification |
| :-----: | :------------ |
| `✅` / `[x]` | Phase **terminée** et validée (commit présent dans l'historique) |
| `⬜` / `[ ]` | Phase **à faire** — aucun travail réalisé pour le moment |

---

## **Vue d'ensemble**

| # | Phase | Objectif | Statut |
| :-: | :---- | :------- | :----: |
| 1 | Fondations du projet | Structure, qualité et CI/CD | ✅ |
| 2 | Cœur fonctionnel | API publiques, providers, validation | ✅ |
| 3 | Tests et vérifications | Couverture, lint, typage, sécurité | ✅ |
| 4 | Documentation | README, CHANGELOG, guides, licence | ✅ |
| 5 | Documentation web statique | Frontend `docs/` + GitHub Pages | ✅ |
| 6 | Améliorations et bilinguisme | Session, lazy Google, URL strictes, docs EN | ✅ |
| 7 | Publication et release | Tag `v0.1.0` + mise en ligne sur PyPI | ⬜ |

---

## **Phase 1 — Fondations du projet** ✅

> **Objectif :** poser une base saine et réutilisable pour un package Python diffusable.

### Détail

- [x] Structure du dépôt (`src/kliz/`, `tests/`, `.github/`)
- [x] `pyproject.toml` complet : métadonnées, dépendances, dev-dependencies, versions Python 3.9 → 3.14
- [x] `.gitignore` et gestion des fichiers cachés (`.venv`, `dist/`, etc.)
- [x] Templates GitHub : `bug_report.yml`, `feature_request.yml`, `PULL_REQUEST_TEMPLATE.md`, `config.yml`
- [x] `CODEOWNERS` et `dependabot.yml` pour la maintenance automatisée
- [x] Workflow `ci.yml` : tests multi-version, lint, typage, build, audit
- [x] Workflow `release.yml` : publication PyPI via Trusted Publishing

---

## **Phase 2 — Cœur fonctionnel** ✅

> **Objectif :** implémenter l'architecture Adapter/Strategy avec les deux moteurs supportés.

### Détail

- [x] `BaseProvider` : contrat minimal `notify(url) -> bool` en `src/kliz/providers/base.py`
- [x] `IndexNowProvider` : notification unitaire (`notify`) et par lots (`notify_many`)
- [x] `GoogleProvider` : publication `URL_UPDATED` via l'API Google Indexing
- [x] `Kliz` : orchestrateur avec résultats simples (`notify_all`) et détaillés (`notify_all_detailed`)
- [x] `parse_http_url` : validation des URL (schéma, hôte, identifiants interdits)
- [x] `exceptions.py` : erreurs structurées avec indication de retry (`retryable`)
- [x] `results.py` : objets de résultat exposés publiquement
- [x] `py.typed` : typage strict exposé aux utilisateurs du package

---

## **Phase 3 — Tests et vérifications** ✅

> **Objectif :** garantir la robustesse sans accès réseau, clé IndexNow ni compte de service Google.

### Détail

- [x] `tests/test_core.py` : orchestrateur, résultats, erreurs
- [x] `tests/test_providers.py` : IndexNow et Google (appels `requests` mockés)
- [x] `tests/test_public_api.py` : contrat public de l'API
- [x] Couverture ≥ 95 % atteinte (97,36 % actuellement), 68 tests verts
- [x] `ruff format` et `ruff check` conformes
- [x] `mypy` strict sans erreur
- [x] `pip-audit` et `twine check --strict` sans alerte

---

## **Phase 4 — Documentation** ✅

> **Objectif :** documenter l'installation, l'usage et les bonnes pratiques en français.

### Détail

- [x] `README.md` : démarrage rapide, architecture, configuration, recettes Celery, production
- [x] `CHANGELOG.md` : historique et section `[Unreleased]`
- [x] `CONTRIBUTING.md` : guide du contributeur
- [x] `SECURITY.md` : politique de sécurité
- [x] `LICENSE` : licence MIT

---

## **Phase 5 — Documentation web statique** ✅

> **Objectif :** offrir une documentation consultable en ligne, sans serveur à maintenir.

### Détail

- [x] `docs/index.html` : documentation statique autonome
- [x] `docs/styles.css` et `docs/app.js` : habillage et interactivité
- [x] `docs/assets/kliz-mark.svg` : identité visuelle du package
- [x] Workflow `pages.yml` : déploiement automatique sur GitHub Pages

---

## **Phase 6 — Améliorations et bilinguisme** ✅

> **Objectif :** durcir l'implémentation, optimiser les connexions réseau et ouvrir le projet à un public international.

### Détail

- [x] **Session HTTP réutilisable** dans `IndexNowProvider` : connexion persistante `requests.Session`, injection possible, méthode `close()`
- [x] **Client Google paresseux** : lecture du fichier compte de service uniquement au premier `notify`, erreurs de configuration non retentables, auto-rétablissement
- [x] **Validation stricte des URL** : fragments (`#`) toujours rejetés, chaînes de requête (`?`) rejetées via `require_clean`
- [x] `README.md` enrichi : sections « Validation des URL », session, client Google paresseux
- [x] `README.en.md` : traduction anglaise complète, reliée à la version française
- [x] `CHANGELOG.en.md` : traduction anglaise du changelog
- [x] Section `[Unreleased]` à jour dans les deux changelogs (Ajouté / Modifié)

---

## **Phase 7 — Publication et release** ⬜

> **Objectif :** diffuser `kliz` sur PyPI et permettre son installation via `pip install kliz`.

> ⚠️ **Non commencée.** Tous les prérequis sont en place (workflow de release déjà configuré) ; il ne reste que l'exécution.

### Détail

- [ ] Vérifier que la version dans `pyproject.toml` (actuellement `0.1.0`) est définitive
- [ ] Créer et pousser le tag `v0.1.0` sur la branche `main`
- [ ] Vérifier que le workflow `release.yml` se déclenche correctement sur le tag
- [ ] Publier `kliz` sur PyPI (relié à l'environnement `pypi`)
- [ ] Vérifier la publication et le badge PyPI dans le README
- [ ] Activer le suivi de version (retirer le statut *Alpha* si souhaité)
- [ ] Revoir `pip install kliz` dans un environnement propre de bout en bout

---

*Document généré à partir de l'historique git du dépôt et du travail déjà réalisé sur les branches `main` et `agent/*`. À mettre à jour au fil des prochaines phases.*