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
