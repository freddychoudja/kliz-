# TODO — Feuille de route `kliz`

> **Statut global :** 🟢 7/7 phases réalisées · livré en **v0.2.0**.
> **Prochaine étape :** 🟡 feuille de route **v0.2.1 → v1.0** (phases 8–24) proposée plus bas —
> à valider et réaliser **une par une**, dans l’ordre.

---

## **Légende**

| Symbole | Signification |
| :-----: | :------------ |
| `✅` / `[x]` | Phase **terminée** — travail réalisé et validé |
| `⬜` / `[ ]` | Phase **à faire** — aucun travail réalisé pour le moment |

---

## **Vue d'ensemble**

| # | Phase | Objectif | Statut |
| :-: | :---- | :------- | :----: |
| 1 | Validation plus stricte des URL | Rejeter les URL « sales » avant tout envoi | ✅ |
| 2 | Réutilisation des connexions | Une session HTTP persistante au lieu d’un tunnel par appel | ✅ |
| 3 | Client Google paresseux | Ne pas lire le compte de service à la création | ✅ |
| 4 | Politique de retry | Backoff exponentiel + jitter, opt-in | ✅ |
| 5 | Orchestration par lots ⭐ | `Kliz.notify_many` : découpage intelligent par provider | ✅ |
| 6 | Échafaudage de providers | Helper `_http.py` + base batch réutilisable | ✅ |
| 7 | Finition & livraison | Version `0.2.0`, docs, vérifications complètes | ✅ |

---

## **Phase 1 — Validation plus stricte des URL** ✅

> **Expliqué simplement :** le videur du club contrôle que chacun a une pièce d’identité, mais
> jamais que cette pièce est propre. Aujourd’hui, il accepte
> `https://example.com/page?utm_source=foo&id=77`. Pour un indexeur, ce n’est pas une adresse
> propre — c’est une adresse avec du bric-à-brac attaché. Si vous dites à Google « indexe cette
> URL avec ses déchets », vous gaspillez votre quota sur des pages qui ne se classeront jamais
> correctement.

> **Objectif :** le videur devient exigeant : il demande « es-tu une adresse nue et propre ? ».

### Travail demandé

- [x] Mettre à jour `parse_http_url` dans `_validation.py` pour **rejeter les URL contenant une
      chaîne de requête (`?`) ou un fragment (`#`)**
- [x] Rendre la stricteur **configurable** (`require_clean`), car le découpage des lots pourra
      réclamer de la tolérance plus tard
- [x] Ajouter les tests correspondants

### Tests attendus

- [x] Une URL propre et valide **passe**
- [x] `?tracking=1` est **rejeté**
- [x] `#section` est **rejeté**

---

## **Phase 2 — Réutilisation des connexions** ✅

> **Expliqué simplement :** imaginez une maison où le facteur reconstruit une route neuve à
> chaque lettre qu’il distribue, puis la démolit. C’est ainsi que fonctionne `requests.post()`
> aujourd’hui — un nouveau tunnel TCP à chaque appel. La solution : construire **une seule**
> route (une `requests.Session`) une fois, et la réutiliser pour toutes les lettres.

> **Objectif :** une seule conduite, de nombreux messages.

### Travail demandé

- [x] `IndexNowProvider` crée une `Session` une seule fois (dans `__init__`)
- [x] La session est réutilisée dans `notify_many`
- [x] Injection possible d’une session externe (tests, proxies, configuration partagée)
- [x] Méthode `close()` pour libérer les connexions proprement
- [x] Aucun changement d’API — invisible pour les utilisateurs

---

## **Phase 3 — Client Google paresseux** ✅

> **Expliqué simplement :** à la création du `GoogleProvider`, le code lit immédiatement le
> fichier de passeport et serre la main de Google. Si le passeport est absent à cet instant,
> tout le programme plante au démarrage — même si vous n’avez jamais prévu d’utiliser Google.
> Correctif : garder le passeport dans le tiroir et ne le sortir qu’au premier envoi réel.

> **Objectif :** le passeport n’est présenté que lorsqu’on le demande.

### Travail demandé

- [x] Encapsuler la construction du service dans une **fonction exécutée une seule fois**, au
      premier `notify` (pattern « lazy »)
- [x] Les erreurs de configuration (fichier absent, JSON invalide) remontent au moment de la
      notification, non au démarrage
- [x] Erreurs de configuration marquées **non retentables** (`retryable=False`)
- [x] Auto-rétablissement du provider dès que le fichier est corrigé
- [x] Tests prouvant que le passeport n’est **pas** lu avant la première notification

---

## **Phase 4 — Politique de retry** ✅

> **Expliqué simplement :** quand une porte est verrouillée mais récupérable (erreurs `429`,
> `5xx`), un facteur malin attend puis réessaie, avec un enthousiasme décroissant : 1 s, puis
> 2 s, puis 4 s (c’est le « backoff »), plus une petite secousse aléatoire (le « jitter ») pour
> que toute la flotte ne frappe pas aux portes à la même seconde.

> **Objectif :** le bon sens du facteur.

### Travail demandé

- [x] Ajouter un paramètre optionnel de retry / `max_attempts` à `Kliz` (ou à l’appel de
      notification)
- [x] Backoff exponentiel + jitter
- [x] **Désactivé par défaut** — la bibliothèque reste simple, le retry est opt-in
- [x] Horloge et `sleep` **injectables** pour la testabilité (aucune vraie attente dans les tests)

---

## **Phase 5 — Orchestration par lots** ⭐ ✅

> **Expliqué simplement :** le chef (`Kliz`) ne sait aujourd’hui dire qu’« une seule URL » à
> chaque travailleur. Or IndexNow peut encaisser 10 000 adresses en **un seul voyage**, tandis
> que Google n’en veut qu’une à la fois. Le chef doit apprendre à découper une liste en lots par
> provider — le gros lot pour IndexNow, chaque adresse individuelle pour Google — tout en
> renvoyant des résultats propres par provider.

> **Objectif :** le patron apprend à déléguer des listes. C’est la **phase phare** : elle
> transforme une bibliothèque « une URL à la fois » en « donnez-nous tout votre sitemap » — ce
> dont les entreprises et administrations ont réellement besoin.

### Travail demandé

- [x] Ajouter `Kliz.notify_many(urls)` et `notify_many_detailed(urls)`
- [x] Appeler `notify_many` sur les providers qui le supportent, **repli en boucle de `notify`**
      pour les autres
- [x] Clés de résultats conservées **par provider**
- [x] Respecter `max_urls_per_request` propre à chaque provider

---

## **Phase 6 — Échafaudage de providers** ✅

> **Expliqué simplement :** construire un adaptateur pour un nouveau moteur équivaut aujourd’hui
> à charpenter toute la maison à partir de zéro. Nous allons prédécouper le bois : une base
> `BatchProvider` qui gère déjà « une URL = un lot d’un », plus une session partagée et une
> boucle `notify_many` prête à l’emploi avec la vérification de l’hôte commun. Les futurs
> moteurs n’auront plus qu’à se décrire et remplir **2 méthodes au lieu de 6**.

> **Objectif :** les constructeurs reçoivent une maison prédécoupée.

### Travail demandé

- [x] Ajouter un helper `_http.py` : création de `Session` partagée + wrapper de requête
- [x] Faire profiter `IndexNowProvider` et la base de ce helper
- [x] Tester qu’un mini-provider fabriqué obtient le comportement par lots **gratuitement**

---

## **Phase 7 — Finition & livraison (v0.2.0)** ✅

> **Expliqué simplement :** mettre le produit fini dans une boîte avec son étiquette : passer la
> version de `0.1.0` à `0.2.0`, mettre à jour le `CHANGELOG.md`, rafraîchir le `README` et la
> documentation avec les nouvelles capacités, puis exécuter la vérification nationale complète.
> Tout doit passer, comme une porte contrôlée par une administration exigeante.

> **Objectif :** livrer proprement, en boîte étiquetée.

### Travail demandé

- [x] Version `0.1.0` → **`0.2.0`** dans `pyproject.toml`
- [x] Mettre à jour le `CHANGELOG.md` (FR/EN)
- [x] Rafraîchir le `README` et la documentation (FR/EN) avec les nouvelles capacités
- [x] Vérification nationale complète : `pytest --cov=95`, `ruff`, `mypy`, `build`, `twine`
- [x] Tout doit passer sans exception

---

# **Feuille de route v0.2.1 → v1.0 — devenir la référence mondiale** 🌍

> **Constat de l’audit (2026-10-08) :** le code est propre (118 tests, 96 % de couverture,
> `ruff` et `mypy --strict` verts), l’architecture provider est saine. Mais trois choses
> empêchent `kliz` de jouer dans la cour des grands : **(1)** deux bugs réels dans le traitement
> par lots, **(2)** une portée limitée (2 moteurs, pas de sitemap, packaging en français,
> dépendances Google lourdes imposées à tous), **(3)** aucun écosystème (GitHub Action,
> intégrations framework, communauté).

## **Vue d’ensemble**

| # | Palier | Phase | Objectif | Statut |
| :-: | :-: | :---- | :------- | :----: |
| 8 | 🔴 v0.2.1 | Lots robustes | Corriger les 2 bugs de `notify_many` + CLI vraiment par lots | ✅ |
| 9 | 🔴 v0.2.1 | Retry intelligent | `Retry-After`, plafond, vrai jitter, échéance globale | ✅ |
| 10 | 🔴 v0.2.1 | Normalisation des URL | `allow_query`, IDN, ports par défaut, dédoublonnage | ✅ |
| 11 | 🟠 v0.3 | Packaging mondial | Anglais d’abord, extra `[google]`, fin de Python 3.9 | ✅ |
| 12 | 🟠 v0.3 | Observabilité | `logging`, hooks d’événements, zéro fuite de secret | ⬜ |
| 13 | 🟠 v0.3 | CLI professionnelle | `--json`, `--dry-run`, stdin, `keygen`/`verify-key`, config | ⬜ |
| 14 | 🟡 v0.4 | Sitemaps ⭐ | « Donnez-nous votre sitemap » : index, gzip, `lastmod` | ✅ |
| 15 | 🟡 v0.4 | État & quotas | Ne notifier que ce qui a changé, respecter les quotas | ⬜ |
| 16 | 🟡 v0.4 | Plus de moteurs + plugins | Bing, Yandex, Naver, Seznam, Baidu… + entry points | ⬜ |
| 17 | 🟡 v0.4 | Async | `AsyncKliz` (extra `httpx`), sûreté multi-thread | ⬜ |
| 18 | 🟢 v0.5 | GitHub Action ⭐ | Notifier automatiquement après chaque déploiement | ⬜ |
| 19 | 🟢 v0.5 | Intégrations | Django, Wagtail, Flask, FastAPI, MkDocs, Docker | ⬜ |
| 20 | 🔵 continu | Tests de niveau mondial | Hypothesis, contrats HTTP, matrice OS, 100 % branches | ⬜ |
| 21 | 🔵 continu | Chaîne d’approvisionnement | Scorecard, CodeQL, zizmor, actions épinglées, SBOM | ⬜ |
| 22 | 🔵 continu | Site de documentation | MkDocs Material + référence API + FR/EN versionnés | ⬜ |
| 23 | 🔵 continu | Communauté | Code de conduite, gouvernance, labels, badges, renommage | ⬜ |
| 24 | 🏁 v1.0 | API stable | Gel de l’API, politique de dépréciation, 1.0.0 | ⬜ |

---

## **Phase 8 — Lots robustes** ✅

> **Expliqué simplement :** le chef envoie un sac de 10 000 lettres à IndexNow. S’il y a
> **une seule** lettre mal adressée dans le sac, ou des lettres pour deux villes différentes
> (`a.com` et `www.a.com`), **tout le sac est refusé** sans même partir. Et la CLI, elle,
> n’utilise même pas le sac : elle poste les lettres une par une.

> **Bugs reproduits :**
> `notify_many(["https://a.com/x", "https://www.a.com/y"])` → échec total (« same host »), 0 envoi.
> `notify_many(["https://a.com/x", "https://a.com/y?id=1"])` → échec total, 0 envoi.

### Travail demandé

- [x] `Kliz.notify_many` : **regrouper par hôte** avant de découper par `max_urls_per_request`
- [x] Pré-valider chaque URL : les invalides deviennent un résultat d’échec **individuel**,
      les valides partent quand même
- [x] Dédoublonner les URL (en conservant l’ordre)
- [x] Ajouter un champ `urls: tuple[str, ...]` à `NotificationResult` (savoir **quelles** URL
      ont échoué)
- [x] `kliz notify --batch` utilise `notify_many_detailed` (1 requête au lieu de N)
- [x] Tests de non-régression pour les deux bugs ci-dessus
- [x] Bonus : IndexNow ne vérifiait que la **première** URL d’un lot contre `key_location`
      — toutes sont maintenant vérifiées ; commentaires `#` indentés ignorés par la CLI

---

## **Phase 9 — Retry intelligent** ✅

> **Expliqué simplement :** quand le serveur répond « 429 — revenez dans 120 s », le facteur
> l’ignore et revient dans 1 s. Et sa « secousse aléatoire » est calculée à partir de
> l’horloge (`random.Random(clock())`), donc pas vraiment aléatoire.

### Travail demandé

- [x] Lire l’en-tête `Retry-After` (secondes ou date HTTP) et le porter dans `ProviderError`
- [x] Plafond de délai (`max_delay`) et échéance totale (`deadline`) optionnels
- [x] Jitter via un `random.Random` injectable (proportionnel, ≤ 25 % — choix : garder un
      délai minimal garanti plutôt que le « full jitter »)
- [x] Bonus : `attempts` et `retry_after` dans les résultats ; `--max-attempts` CLI ;
      entrée `max-attempts` de l’Action (3 par défaut)
- [x] Documenter la différence avec `GoogleProvider(num_retries=…)` (double retry possible)

---

## **Phase 10 — Normalisation des URL** ✅

> **Expliqué simplement :** beaucoup de sites légitimes ont des URL canoniques avec `?`
> (WordPress `?p=123`, fiches produit). Les refuser toujours, c’est fermer la porte à une
> grosse partie du web. Inversement, `HTTPS://Example.com:443/a` et `https://example.com/a`
> sont la même page et ne doivent pas consommer deux fois le quota.

### Travail demandé

- [x] Option `allow_query=False` sur les providers (strict par défaut, ouvrable)
- [x] Normaliser : schéma/hôte en minuscules, IDN → punycode, suppression des ports par défaut
- [x] Fonction publique `kliz.normalize_url()` réutilisable par les applications
- [x] Bonus : encodage des caractères non sûrs ; dédoublonnage sur la forme normalisée ;
      `--allow-query` CLI et entrée `allow-query` de l’Action

---

## **Phase 11 — Packaging mondial** ✅

> **Expliqué simplement :** la vitrine PyPI est en français, et installer `kliz` pour
> IndexNow seul télécharge toute la bibliothèque Google (~plusieurs dizaines de Mo). Un
> développeur de Tokyo ou de São Paulo repart avant d’avoir essayé.

### Travail demandé

- [x] `README.md` en anglais (vitrine PyPI) ; version française dans `README.fr.md`
      (idem `CHANGELOG`, `CONTRIBUTING`, description `pyproject`, aide de la CLI)
- [x] Dépendances Google dans un extra : `pip install kliz[google]` ; le cœur ne dépend que
      de `requests` ; message d’erreur clair si l’extra manque
- [x] Supprimer Python 3.9 (fin de vie octobre 2025) ; aligner `ruff target-version` et
      `mypy python_version` (aujourd’hui incohérents : py39 vs 3.10)
- [x] Classifier `Development Status :: 4 - Beta`, mots-clés enrichis (bing, yandex, sitemap…)
- [x] Mesuré : `pip install kliz` = 7 paquets / ~4 Mo (contre 24 / ~144 Mo avant)
- [ ] Reste : le site statique `docs/index.html` est encore en français → Phase 22

---

## **Phase 12 — Observabilité** 🟠

> **Expliqué simplement :** en production, `kliz` est muet : aucun log. Quand ça casse à
> 3 h du matin, personne ne sait ce qui s’est passé.

### Travail demandé

- [ ] `logging.getLogger("kliz")` : requêtes, statuts, tentatives, délais (niveau DEBUG/INFO)
- [ ] Hook optionnel `on_result` / `on_retry` sur `Kliz` (métriques, Prometheus, OTel)
- [ ] Test garantissant que la clé IndexNow n’apparaît **jamais** dans les logs ni les erreurs

---

## **Phase 13 — CLI professionnelle** 🟠

### Travail demandé

- [ ] `--json` (sortie machine pour CI/scripts), lecture depuis stdin (`-`)
- [x] `--dry-run`
- [x] `--max-attempts`
- [ ] `--timeout`
- [x] `kliz indexnow keygen` (génère une clé + le fichier à publier)
- [x] `kliz indexnow verify-key` (vérifie que le fichier clé est bien servi en ligne,
      y compris le piège « 200 + page HTML » des SPA, testé sur almight.me)
- [ ] Configuration par fichier : `[tool.kliz]` dans `pyproject.toml` ou `kliz.toml`
- [x] Ignorer les lignes `#` même indentées (bug mineur : `line.startswith("#")` sans `strip`)

---

## **Phase 14 — Sitemaps** ⭐ ✅

> **Expliqué simplement :** personne ne veut taper ses URL une à une. Le geste naturel est
> « voici mon sitemap, débrouille-toi ». C’est la fonctionnalité qui fera dire « wow ».

### Travail demandé

- [x] `kliz.sitemap.iter_urls(url_or_path)` : sitemap simple, index de sitemaps, `.xml.gz`
- [x] Parsing XML sécurisé (`defusedxml`), limites de taille (50 000 URL / 50 Mo)
- [x] Filtre `since=` sur `<lastmod>`
- [x] `kliz notify --sitemap https://… --since 2026-10-01` (+ `--dry-run`)
      — choix : pas de `Kliz.notify_sitemap()`, `notify_many(read_sitemap(...))` suffit
- [x] Validé sur https://almight.me/sitemap.xml : 7 pages, images ignorées

---

## **Phase 15 — État & quotas** 🟡

> **Expliqué simplement :** renvoyer tout le sitemap à chaque déploiement gaspille le quota
> (Google : 200 notifications/jour par défaut). Il faut une mémoire de ce qui a déjà été envoyé.

### Travail demandé

- [ ] Interface `StateStore` + implémentations fichier JSON et SQLite (stdlib)
- [ ] Ne notifier que les URL nouvelles ou dont `lastmod` a changé
- [ ] Budget de quota par provider (s’arrêter proprement, reprendre le lendemain)

---

## **Phase 16 — Plus de moteurs + plugins** 🟡

### Travail demandé

- [ ] Endpoints IndexNow dédiés sélectionnables (Bing, Yandex, Seznam, Naver, Yep)
- [ ] `BingUrlSubmissionProvider` (API Bing Webmaster)
- [ ] `BaiduProvider` (API push Baidu — indispensable pour le marché chinois)
- [x] `GoogleSearchConsoleProvider` : soumission du sitemap via l’API Search Console
      (la voie officielle pour **tous** les sites, contrairement à l’API Indexing)
- [ ] `GoogleProvider` : `URL_DELETED` + requêtes groupées (batch HTTP de 100)
- [ ] API `notify(url, action="updated" | "deleted")` commune
- [ ] Découverte de providers tiers via entry points `kliz.providers` (`kliz-<moteur>` sur PyPI)

---

## **Phase 17 — Async** 🟡

### Travail demandé

- [ ] `AsyncKliz` + providers async basés sur `httpx` (extra `kliz[async]`), envois parallèles
- [ ] Documenter et tester la sûreté multi-thread (sessions, client Google)

---

## **Phase 18 — GitHub Action** ⭐ 🟢

> **Expliqué simplement :** le meilleur levier d’adoption. Trois lignes de YAML et chaque
> déploiement d’un site (Hugo, Astro, Next.js, Jekyll, MkDocs…) prévient les moteurs.

### Travail demandé

- [x] `action.yml` à la racine : entrées `sitemap`, `urls`, `since`, clés, `dry-run`,
      vérification de clé ; job CI d’exécution à blanc
- [ ] Mode « diff » : ne notifier que les pages modifiées par le commit
- [ ] Publication sur le GitHub Marketplace (exige un dépôt **sans workflows** :
      dupliquer `action.yml` dans un dépôt dédié `kliz-action`)
- [ ] Image Docker officielle (`ghcr.io/…/kliz`) pour GitLab CI, cron, Kubernetes

---

## **Phase 19 — Intégrations framework** 🟢

> Paquets séparés pour garder le cœur agnostique (règle de `CONTRIBUTING.md`).

- [ ] `kliz-django` : signal `post_save`/`post_delete`, réglages, commande de gestion
- [ ] Recettes ou paquets : Wagtail, Flask, FastAPI, plugin MkDocs, hook Sphinx

---

## **Phase 20 — Tests de niveau mondial** 🔵

- [ ] Tests par propriétés (`hypothesis`) sur la validation/normalisation des URL
- [ ] Tests de contrat HTTP (`responses`) avec les vrais formats de payload IndexNow/Google
- [ ] Matrice CI Linux + macOS + Windows
- [ ] 100 % de couverture des branches (manquent : `cli.py` 32-40, `indexnow.py` 50/76/82)
- [ ] Test « smoke » optionnel contre la vraie API IndexNow (workflow manuel, secret)

---

## **Phase 21 — Chaîne d’approvisionnement** 🔵

- [ ] OpenSSF Scorecard + badge, workflow CodeQL
- [ ] `zizmor` pour auditer les workflows ; actions épinglées par SHA
- [ ] `pre-commit` (ruff, mypy, fin de ligne) ; `release-please` pour changelog automatique
- [ ] Attestations PyPI (Trusted Publishing) + SBOM CycloneDX dans les releases

---

## **Phase 22 — Site de documentation** 🔵

- [ ] Migrer `docs/` vers MkDocs Material + `mkdocstrings` (référence API générée)
- [ ] i18n FR/EN, versions multiples (`mike`), guides « recettes » par framework
- [ ] Page « Pourquoi kliz ? » avec comparatif honnête des alternatives

---

## **Phase 23 — Communauté** 🔵

- [ ] `CODE_OF_CONDUCT.md` (Contributor Covenant), `GOVERNANCE.md`, `SUPPORT.md`
- [ ] Labels `good first issue` / `help wanted`, GitHub Discussions, Project board public
- [ ] Badges : version PyPI, téléchargements, couverture (Codecov), Scorecard
- [ ] Renommer le dépôt `kliz-` → `kliz` (le tiret final nuit à la découvrabilité)
- [ ] Bannière/logo, GIF de démo dans le README (réutiliser `demo-output/`)

---

## **Phase 24 — API stable (v1.0)** 🏁

- [ ] Revue complète de l’API publique (`__all__`), gel des signatures
- [ ] Politique de dépréciation écrite (≥ 1 version mineure d’avertissement)
- [ ] Release `1.0.0`, annonce (Python Weekly, Reddit r/Python, Hacker News, dev.to)

---

## **Annexe — Outils et « super-pouvoirs » à mobiliser**

| Besoin | Outil |
| :----- | :---- |
| Recherche des specs (IndexNow, Bing, Baidu, Google batch) | Recherche web Claude Code |
| Revue de chaque phase avant fusion | `/code-review`, `/security-review`, `/simplify` |
| Vérifier la CLI / le site doc en vrai | `/run`, Claude in Chrome (captures du site) |
| Suivi CI des PR | `gh` CLI, `/loop` pour surveiller les workflows |
| Tests | `hypothesis`, `responses`, `pytest-cov` |
| Docs | `mkdocs-material`, `mkdocstrings`, `mike` |
| Sécurité | `pip-audit`, `zizmor`, CodeQL, OpenSSF Scorecard |
| Release | `release-please`, PyPI Trusted Publishing |

---

*Document généré à partir des phases discutées ensemble et du travail déjà réalisé sur la
branche `main`. Les phases 1–7 sont livrées dans `0.2.0` ; les phases 8–24 sont une
proposition issue de l’audit du 2026-10-08.*
