# Typage : mypy en intégration continue

Version 0.8.2 · Sprint 4, lot 6 · décision A8 du PO (02/11/2026) · revue du 30/10, Q5

## 1. Deux niveaux

| Niveau | Modules | Mode | Effet sur une PR |
|---|---|---|---|
| Étape 1 | `contracts/`, `scoring/`, `indicators/`, `reports/` (contrats partagés et modules du Sprint 4) | `strict`, **bloquant** | Une erreur de type empêche la fusion, comme un test rouge |
| Étapes 2 et 3 | `rules/`, `import_engine/`, `api/` | `strict`, **rapport seulement** (`continue-on-error`) | La CI affiche les erreurs mais reste verte |

Tout nouveau module entre directement dans l'étape 1 (liste `files` de `[tool.mypy]`, `backend/pyproject.toml`).

## 2. Configuration

- `strict = true`, `warn_unused_ignores = true`, plugin `pydantic.mypy`.
- **`Any` interdit** (`disallow_any_explicit`), sauf dans `contracts/json_types.py`, qui nomme les deux seules frontières non typées : `JsonDict` (un fichier JSON de `reference/`) et `Row` (une ligne de tableau : le numéro sous `_row`, puis des textes ou `None`).
- **Bibliothèques sans types** : déclarées module par module (`ignore_missing_imports`), jamais en global. Aujourd'hui : aucune (`duckdb`, jamais importé, a été retiré par CL-45). `lxml-stubs` est installé ; Polars, FastAPI et Pydantic sont typés.
- Les tests ne sont pas vérifiés.

## 3. Lancer en local

```bash
cd backend
uv run mypy                               # étape 1, comme la CI
uv run mypy rules import_engine api       # rapport des étapes 2 et 3
```

## 4. Dette mesurée (02/11/2026, 0.8.2)

| Module | Erreurs en mode strict |
|---|---|
| `rules/` | 67 |
| `import_engine/` | 4 |
| `api/` | 73 |

Ces nombres doivent baisser au fil des sprints ; un module passe en étape 1 dès qu'il atteint zéro.
