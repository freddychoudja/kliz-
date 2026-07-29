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

