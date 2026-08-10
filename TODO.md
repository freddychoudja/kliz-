# TODO — Feuille de route `kliz`

> **Statut global :** 🟢 3/7 phases réalisées · la suite mène à la v0.2.0.

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
| 4 | Politique de retry | Backoff exponentiel + jitter, opt-in | ⬜ |
| 5 | Orchestration par lots ⭐ | `Kliz.notify_many` : découpage intelligent par provider | ⬜ |
| 6 | Échafaudage de providers | Helper `_http.py` + base batch réutilisable | ⬜ |
| 7 | Finition & livraison | Version `0.2.0`, docs, vérifications complètes | ⬜ |

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

## **Phase 4 — Politique de retry** ⬜

> **Expliqué simplement :** quand une porte est verrouillée mais récupérable (erreurs `429`,
> `5xx`), un facteur malin attend puis réessaie, avec un enthousiasme décroissant : 1 s, puis
> 2 s, puis 4 s (c’est le « backoff »), plus une petite secousse aléatoire (le « jitter ») pour
> que toute la flotte ne frappe pas aux portes à la même seconde.

> **Objectif :** le bon sens du facteur.

### Travail demandé

- [ ] Ajouter un paramètre optionnel de retry / `max_attempts` à `Kliz` (ou à l’appel de
      notification)
- [ ] Backoff exponentiel + jitter
- [ ] **Désactivé par défaut** — la bibliothèque reste simple, le retry est opt-in
- [ ] Horloge et `sleep` **injectables** pour la testabilité (aucune vraie attente dans les tests)

---

## **Phase 5 — Orchestration par lots** ⭐ ⬜

> **Expliqué simplement :** le chef (`Kliz`) ne sait aujourd’hui dire qu’« une seule URL » à
> chaque travailleur. Or IndexNow peut encaisser 10 000 adresses en **un seul voyage**, tandis
> que Google n’en veut qu’une à la fois. Le chef doit apprendre à découper une liste en lots par
> provider — le gros lot pour IndexNow, chaque adresse individuelle pour Google — tout en
> renvoyant des résultats propres par provider.

> **Objectif :** le patron apprend à déléguer des listes. C’est la **phase phare** : elle
> transforme une bibliothèque « une URL à la fois » en « donnez-nous tout votre sitemap » — ce
> dont les entreprises et administrations ont réellement besoin.

### Travail demandé

- [ ] Ajouter `Kliz.notify_many(urls)` et `notify_many_detailed(urls)`
- [ ] Appeler `notify_many` sur les providers qui le supportent, **repli en boucle de `notify`**
      pour les autres
- [ ] Clés de résultats conservées **par provider**
- [ ] Respecter `max_urls_per_request` propre à chaque provider

---

## **Phase 6 — Échafaudage de providers** ⬜

> **Expliqué simplement :** construire un adaptateur pour un nouveau moteur équivaut aujourd’hui
> à charpenter toute la maison à partir de zéro. Nous allons prédécouper le bois : une base
> `BatchProvider` qui gère déjà « une URL = un lot d’un », plus une session partagée et une
> boucle `notify_many` prête à l’emploi avec la vérification de l’hôte commun. Les futurs
> moteurs n’auront plus qu’à se décrire et remplir **2 méthodes au lieu de 6**.

> **Objectif :** les constructeurs reçoivent une maison prédécoupée.

### Travail demandé

- [ ] Ajouter un helper `_http.py` : création de `Session` partagée + wrapper de requête
- [ ] Faire profiter `IndexNowProvider` et la base de ce helper
- [ ] Tester qu’un mini-provider fabriqué obtient le comportement par lots **gratuitement**

---

## **Phase 7 — Finition & livraison (v0.2.0)** ⬜

> **Expliqué simplement :** mettre le produit fini dans une boîte avec son étiquette : passer la
> version de `0.1.0` à `0.2.0`, mettre à jour le `CHANGELOG.md`, rafraîchir le `README` et la
> documentation avec les nouvelles capacités, puis exécuter la vérification nationale complète.
> Tout doit passer, comme une porte contrôlée par une administration exigeante.

> **Objectif :** livrer proprement, en boîte étiquetée.

### Travail demandé

- [ ] Version `0.1.0` → **`0.2.0`** dans `pyproject.toml`
- [ ] Mettre à jour le `CHANGELOG.md` (FR/EN)
- [ ] Rafraîchir le `README` et la documentation (FR/EN) avec les nouvelles capacités
- [ ] Vérification nationale complète : `pytest --cov=95`, `ruff`, `mypy`, `build`, `twine`
- [ ] Tout doit passer sans exception

---

*Document généré à partir des phases discutées ensemble et du travail déjà réalisé sur la
branche `main`. À mettre à jour au fil des prochaines phases.*