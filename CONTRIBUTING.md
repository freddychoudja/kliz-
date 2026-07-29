# Contribuer à kliz

Merci de contribuer à `kliz`. Le projet cherche à conserver un cœur léger,
agnostique et simple à intégrer.

## Principes d'architecture

Toute contribution doit préserver les contraintes suivantes :

- aucune dépendance à Django, Celery, Redis ou à un autre framework
  d'application dans `src/kliz` ;
- les moteurs de recherche sont intégrés sous forme de providers héritant de
  `BaseProvider` ;
- les appels réseau doivent avoir un timeout et rester mockables ;
- aucun secret, jeton ou fichier de compte de service ne doit être versionné.

## Préparer l'environnement

```bash
git clone https://github.com/freddychoudja/kliz-.git
cd kliz-
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff format --check src tests
ruff check src tests
mypy src
pytest --cov=kliz
```

## Proposer une modification

1. Ouvrez d'abord une issue pour les changements importants.
2. Créez une branche dédiée depuis `main`.
3. Ajoutez ou adaptez les tests.
4. Vérifiez que `pytest` passe sans accès à de vraies API.
5. Ouvrez une pull request décrivant le problème et la solution.

Les changements doivent rester ciblés. Une pull request ne doit pas contenir
de refactoring sans rapport avec son objectif.

## Ajouter un provider

Un nouveau provider doit :

1. hériter de `kliz.providers.base.BaseProvider` ;
2. implémenter `notify(self, url: str) -> bool` ;
3. retourner `True` après une notification réussie ;
4. laisser remonter les erreurs de l'API distante ;
5. être couvert par des tests utilisant des mocks.

## Préparer une release

1. Mettez à jour la version dans `pyproject.toml`.
2. Déplacez les changements de `Unreleased` vers cette version dans
   `CHANGELOG.md`.
3. Vérifiez localement tests, qualité, audit et distributions.
4. Fusionnez sur `main` après validation de la CI.
5. Créez et poussez un tag `vX.Y.Z` correspondant exactement à la version.

Le workflow `release.yml` construit les distributions puis les publie avec le
Trusted Publishing de PyPI. Aucun token PyPI permanent ne doit être ajouté aux
secrets GitHub.

## Signaler une vulnérabilité

N'ouvrez pas d'issue publique pour une vulnérabilité. Utilisez le canal privé
décrit dans [SECURITY.md](SECURITY.md).