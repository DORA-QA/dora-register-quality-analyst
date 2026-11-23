# Contribuer à DORA QA

Merci de votre intérêt ! Les contributions sont acceptées sous licence **EUPL 1.2** : en proposant une modification, vous acceptez qu'elle soit publiée sous cette licence.

## Règle absolue : aucune donnée réelle

N'ajoutez jamais à une issue, une pull request ou un fichier du dépôt un registre réel, même partiel ou anonymisé à la main. Utilisez les jeux fictifs de `sample-data/` ou les mutations de `backend/tests/cases/`.

## Signaler un constat erroné

Ouvrez une issue avec le modèle « Constat erroné » : code du constat (ex. `DAT-005`), ce que l'outil dit, ce que vous attendiez, et la source réglementaire qui vous fait penser qu'il se trompe (règle EBA, article de l'ITS, note de l'autorité).

## Proposer du code

1. Créez une branche à partir de `main`.
2. Backend (Python 3.13, uv) :
   ```bash
   cd backend && uv sync --frozen
   uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
   ```
3. Frontend (Node.js 22) :
   ```bash
   cd frontend && npm ci
   npm run lint && npm run format:check && npm run test && npm run build
   ```
4. Ajoutez l'en-tête `SPDX-License-Identifier: EUPL-1.2` en tête de tout nouveau fichier source.
5. Ouvrez une pull request qui explique le besoin et la source réglementaire. La CI doit être verte.

Un nouveau contrôle suppose : une entrée dans `backend/reference/messages/catalog.json` (sévérité, origine, référence), ses textes en français et en anglais (`fr.json`, `en.json`), son entrée dans `backend/reference/checks/checks.json`, et au moins une mutation de test qui le déclenche.

## Code de conduite

Échanges courtois et factuels, centrés sur les textes et le code.
