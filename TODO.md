# TODO — Avancement des phases discutées ensemble

> **Statut global :** 🟢 4 phases réalisées · 1 phase restante (publication).

---

## **Légende**

| Symbole | Signification |
| :-----: | :------------ |
| `✅` / `[x]` | Phase **terminée** — travail réalisé dans cette session |
| `⬜` / `[ ]` | Phase **à faire** — aucun travail réalisé pour le moment |

---

## **Vue d'ensemble**

| # | Phase | Objectif | Statut |
| :-: | :---- | :------- | :----: |
| 1 | Session HTTP réutilisable | Optimiser les connexions réseau d’IndexNow | ✅ |
| 2 | Client Google paresseux | Différer la lecture du compte de service | ✅ |
| 3 | Validation stricte des URL | Interdire fragments et chaînes de requête | ✅ |
| 4 | Documentation et bilinguisme | README + CHANGELOG enrichis (FR/EN) | ✅ |
| 5 | Publication et release | Tag `v0.1.0` + mise en ligne sur PyPI | ⬜ |

---

## **Phase 1 — Session HTTP réutilisable** ✅

> **Objectif :** ne pas reconstruire une connexion TCP + poignée de main TLS à chaque
> notification IndexNow.

### Détail

- [x] Instauration d’une connexion persistante `requests.Session` dans `IndexNowProvider`
- [x] Injection possible d’une session externe (tests, proxies, config réseau partagée)
- [x] Méthode `close()` pour libérer proprement les connexions à l’arrêt de l’application
- [x] Documentation du comportement dans le README et le CHANGELOG

---

## **Phase 2 — Client Google paresseux** ✅

> **Objectif :** ne pas lire le fichier du compte de service à la création du provider,
> mais seulement au premier `notify`.

### Détail

- [x] Construction du client Google Indexing reportée au premier appel de `notify`
- [x] Erreurs de configuration (fichier absent, JSON invalide) remontées au bon moment
- [x] Erreurs de configuration marquées **non retentables** (`retryable=False`)
- [x] Auto-rétablissement du provider dès que le fichier est corrigé
- [x] Documentation du comportement dans le README et le CHANGELOG

---

## **Phase 3 — Validation stricte des URL** ✅

> **Objectif :** garantir qu’on ne soumette jamais aux moteurs une URL non canonique.

### Détail

- [x] Les **fragments** (`#...`) sont toujours rejetés
- [x] Les **chaînes de requête** (`?...`) sont rejetées pour les notifications
- [x] Nouveau mode `require_clean` de `parse_http_url` (défaut `False` pour ne pas casser l’existant)
- [x] Section « Validation des URL » ajoutée au README
- [x] Entrée « Modifié » dans le CHANGELOG

---

## **Phase 4 — Documentation et bilinguisme** ✅

> **Objectif :** documenter les nouveautés et ouvrir le projet à un public international.

### Détail

- [x] `README.md` enrichi : validation des URL, session HTTP, client Google paresseux
- [x] `README.en.md` : traduction anglaise complète, reliée à la version française
- [x] `CHANGELOG.md` : section `[Unreleased]` complétée (Ajouté / Modifié)
- [x] `CHANGELOG.en.md` : traduction anglaise du changelog
- [x] Liens croisés FR ⇄ EN dans les deux documents

---

## **Phase 5 — Publication et release** ⬜

> **Objectif :** diffuser `kliz` sur PyPI et permettre son installation via `pip install kliz`.

> ⚠️ **Non commencée.** Tous les prérequis sont en place (workflow de release déjà configuré) ;
> il ne reste que l’exécution.

### Détail

- [ ] Vérifier que la version dans `pyproject.toml` (actuellement `0.1.0`) est définitive
- [ ] Créer et pousser le tag `v0.1.0` sur la branche `main`
- [ ] Vérifier que le workflow `release.yml` se déclenche correctement sur le tag
- [ ] Publier `kliz` sur PyPI (relié à l’environnement `pypi`)
- [ ] Vérifier la publication et le badge PyPI dans le README
- [ ] Activer le suivi de version (retirer le statut *Alpha* si souhaité)
- [ ] Revoir `pip install kliz` dans un environnement propre de bout en bout

---

*Document généré à partir des phases discutées ensemble dans cette session et du travail
déjà réalisé sur la branche `main`. À mettre à jour au fil des prochaines phases.*