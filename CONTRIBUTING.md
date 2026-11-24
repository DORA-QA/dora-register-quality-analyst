# Contribuer à DORA QA / Contributing to DORA QA

[Français](#français) · [English](#english)

## Français

Merci de votre intérêt ! Les contributions sont acceptées sous licence **EUPL 1.2** : en proposant une modification, vous acceptez qu'elle soit publiée sous cette licence.

### Règle absolue : aucune donnée réelle

N'ajoutez jamais à une issue, une pull request ou un fichier du dépôt un registre réel, même partiel ou anonymisé à la main. Utilisez les jeux fictifs de `sample-data/` ou les mutations de `backend/tests/cases/`.

### Signaler un constat erroné

Ouvrez une issue avec le modèle « Constat erroné » : code du constat (ex. `DAT-005`), ce que l'outil dit, ce que vous attendiez, et la source réglementaire qui vous fait penser qu'il se trompe (règle EBA, article de l'ITS, note de l'autorité).

### Proposer du code

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

### Code de conduite

Échanges courtois et factuels, centrés sur les textes et le code.

## English

Thank you for your interest! Contributions are accepted under the **EUPL 1.2** licence: by proposing a change, you agree that it is published under this licence.

### Absolute rule: no real data

Never add a real register to an issue, a pull request or a file of the repository, not even partially or anonymised by hand. Use the fictitious data sets of `sample-data/` or the mutations of `backend/tests/cases/`.

### Reporting a wrong finding

Open an issue with the "Wrong finding" template: code of the finding (e.g. `DAT-005`), what the tool says, what you expected, and the regulatory source that makes you think it is wrong (EBA rule, article of the ITS, note of the authority).

### Proposing code

1. Create a branch from `main`.
2. Backend (Python 3.13, uv):
   ```bash
   cd backend && uv sync --frozen
   uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
   ```
3. Frontend (Node.js 22):
   ```bash
   cd frontend && npm ci
   npm run lint && npm run format:check && npm run test && npm run build
   ```
4. Add the header `SPDX-License-Identifier: EUPL-1.2` at the top of every new source file.
5. Open a pull request that explains the need and the regulatory source. The CI must be green.

A new check requires: an entry in `backend/reference/messages/catalog.json` (severity, origin, reference), its texts in French and English (`fr.json`, `en.json`), its entry in `backend/reference/checks/checks.json`, and at least one test mutation that triggers it.

### Code of conduct

Courteous, factual exchanges, focused on the texts and the code.
