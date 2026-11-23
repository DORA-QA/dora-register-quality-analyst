# Architecture

Ce document décrit l'architecture de ROI Quality Engine, ses couches, ses conventions de code et
ses règles de découplage. Il reflète l'état de la version 0.7.0 (fin du Sprint 2) et indique où
viendront les modules des sprints suivants.

## 1. Vue d'ensemble

```text
        Navigateur
            │
            ▼
┌───────────────────────┐
│ Frontend              │  React, TypeScript, Vite, Material UI
│ nginx, port 3000      │  Fichiers statiques
└───────────┬───────────┘
            │ nginx relaie le port 8000 (HTTP, JSON)
            ▼  réseau Docker interne, sans accès à internet
┌───────────────────────┐
│ Backend               │  Python 3.13, FastAPI, Pydantic
│ uvicorn, port 8000    │  aucun port publié
│                       │
│  api ──► import_engine│
│      ──► dataset      │
│      ──► rules        │
│      ──► scoring      │
│      ──► reports      │
│                       │
│  contracts (partagé)  │
└───────────────────────┘
```

Deux conteneurs, lancés par `docker compose up`. Le navigateur charge l'application sur le port
3000 et appelle l'API sur le port 8000. Ces deux ports sont publiés par le conteneur frontend, sur
`127.0.0.1` seulement : nginx sert l'application et relaie le port 8000 vers le backend. Le backend
vit sur un réseau Docker interne, sans route vers internet et sans port publié ; le conteneur
frontend est sa seule porte (contrôlé par `tests/test_deployment_security.py`). L'API autorise
uniquement l'origine du frontend local (CORS), et nginx impose une politique de sécurité du
contenu qui interdit tout appel vers un autre hôte.

Il n'y a ni base de données, ni volume Docker, ni service externe.

## 2. Couches applicatives du backend

| Module          | Rôle                                                                  | État    |
| --------------- | --------------------------------------------------------------------- | ------- |
| `api`           | Couche HTTP et services d'enchaînement. Aucune règle métier.          | Sprint 1 |
| `contracts`     | Modèles échangés entre modules, catalogue des messages, conventions de nommage, référentiel des versions, lecture des tableaux du jeu de données (`contracts/tables.py`, partagée par `rules` et `indicators`). | Sprint 1 |
| `import_engine` | Détection du type de fichier, validation XML, extraction et validation du ZIP, validation du package, import CSV. | Sprint 1 |
| `dataset`       | Construction du `RoIDataset` et conservation en mémoire.              | Sprint 1 |
| `rules`         | Moteur de règles et règles. Cœur de la valeur du produit. Sprint 2 : contrôles techniques (`rules/technical/`) et règles conditionnelles de l'EBA (`rules/eba_conditional.py`). Sprint 3 : contrôles croisés, métier et de qualité (`rules/business/`, un module par famille). | Sprints 2 et 3 |
| `indicators`    | Indicateurs calculés sur le jeu de données et renvoyés par l'API, sans constat ni score. Sprint 3 : concentration (`docs/concentration.md`). | Sprint 3 |
| `scoring`       | Transformation des constats en indicateurs. Les scores provisoires (confiance, qualité) sont aujourd'hui calculés dans `contracts/check_report.py` ; ils rejoindront ce module au Sprint 4. | Sprint 4 |
| `reports`       | Génération du rapport HTML.                                           | Sprint 4 |
| `reference`     | Données, sans code : messages, versions de taxonomie, schémas XSD.    | Sprint 1 |
| `tests`         | Tests unitaires, tests d'API et tests d'architecture.                 | continu |

### Chaîne d'import

```text
Fichier déposé
   │
   ▼
1. Détection du type ──────────── UNKNOWN : arrêt
   │
   ├── XML ─► 2. Validation XML ─► 3. Extraction du ZIP (stratégie OneGate)
   │                                        │
   ▼                                        ▼
4. Validation du ZIP (lisible, intact, sans danger)
   │
   ▼
5. Validation du package (structure, nommage, version, modèles, paramètres)
   │
   ▼
6. Import des CSV (Polars, tout en texte)
   │
   ├── enveloppe OneGate : destinataire et domaine contrôlés si l'autorité
   │   compétente déclarée (RT.01.01.0050) est l'ACPR (ENV-005, ENV-006)
   ▼
7. RoIDataset en mémoire
   │
   ▼
8. Règles techniques (clés, champs obligatoires, identifiants, longueurs, règles de l'EBA)
```

Chaque étape est une classe de `import_engine` qui respecte un contrat de
`contracts/interfaces.py` et renvoie un résultat portant ses constats. L'enchaînement est fait par
`api/services/import_service.py`, seul endroit qui connaît toutes les étapes. Il ne s'arrête que
si l'étape suivante est techniquement impossible.

### Points d'extension

| Besoin | Où intervenir |
| --- | --- |
| Enveloppe d'une autre autorité | Nouvelle stratégie dans `import_engine`, ajoutée à `default_strategies()` |
| Validation XSD | Fichier `.xsd` déposé dans `reference/xsd/` |
| Nouvelle version de taxonomie | Entrée dans `reference/dora/versions.json` |
| Texte d'un constat | `reference/messages/<langue>.json` |
| Sévérité, type de source ou codes officiels d'un constat | `reference/messages/catalog.json` |
| Autre langue | Voir « Langues » ci-dessous |

### Constats

Un constat (`ValidationMessage`) porte : un code stable (`PKG-010`), une sévérité, le constat, une
explication en clair, une action corrective, un conseil d'expert (cause habituelle, manière de
corriger, pièges), la source du contrôle et, quand ils existent, les
codes utilisés par les autorités pour le même constat (`EBA.808`). La source est typée :
réglementaire, guide officiel ou contrôle propre au produit. Une référence non vérifiée de
première main est marquée comme telle.

Un constat est conservé sans aucun texte : un code, ses paramètres et un détail technique. Les
textes ne sont produits qu'à l'affichage, dans la langue demandée (`render_message`). Le test
`tests/test_message_catalog.py` échoue si
une entrée n'a pas d'explication, d'action corrective ou de source, ou si un constat à corriger
n'a pas de conseil d'expert.

### Langues

Le produit est disponible en anglais (langue de repli) et en français.

| Élément | Où sont les textes | Comment la langue est choisie |
| --- | --- | --- |
| Constats, étapes, erreurs de l'API | `backend/reference/messages/<langue>.json` | Paramètre `lang`, sinon en-tête `Accept-Language`, sinon anglais |
| Libellés de l'interface | `frontend/src/i18n/<langue>.ts` | Sélecteur de l'en-tête ; choix mémorisé dans le navigateur ; à défaut, langue du navigateur |

Principes :

- les moteurs n'écrivent aucun mot : là où il faut une phrase (un motif, un format attendu), ils
  désignent un fragment par sa clé (`fragment("json_invalid")`), écrit dans les fichiers de langue ;
- les codes (`PKG-010`), sévérités, statuts, codes de tables et références du règlement ne sont
  jamais traduits ;
- changer de langue ne relance aucun contrôle : l'interface relit l'import (l'un des deux derniers) avec
  `GET /api/import/{id}?lang=...` ;
- un texte absent d'une langue est remplacé par le texte anglais ;
- les tests échouent si une langue n'a pas exactement les mêmes codes et les mêmes paramètres que
  l'anglais.

Pour ajouter une langue :

1. copier `backend/reference/messages/en.json` vers `<langue>.json` et traduire les textes, sans
   toucher aux clés ni aux paramètres entre accolades ;
2. copier `frontend/src/i18n/en.ts` vers `<langue>.ts`, traduire, puis déclarer la langue dans
   `frontend/src/i18n/context.ts` (`LANGUAGES`, `DICTIONARIES`, `LANGUAGE_NAMES`) ;
3. lancer les tests : ils signalent toute clé manquante.

### Conventions de nommage métier

| Objet | Convention | Exemple |
| --- | --- | --- |
| Table | Code officiel du modèle | `B_01.01` |
| Colonne | Code de la colonne dans le CSV | `c0010` |
| Référence affichée | Style EBA, dérivée par `contracts/naming.py` (`field_reference`) ; le numéro du règlement (`RT.xx`) n'est qu'un complément | `B_01.01.0010` |
| Numéro de ligne | Colonne technique `_row`, rang de la ligne de données à partir de 1 | `2` |

## 3. Règles de découplage

### Sens des dépendances

```text
api ──► import_engine, dataset, rules, indicators, scoring, reports
                    │
                    ▼
                contracts
```

1. `contracts` ne dépend d'aucun autre module du backend.
2. Chaque moteur (`import_engine`, `dataset`, `rules`, `indicators`, `scoring`, `reports`) dépend uniquement de
   `contracts`. Deux moteurs ne s'importent jamais entre eux.
3. Seul `api` connaît tous les moteurs et les enchaîne.
4. Aucun moteur ne dépend de FastAPI ni du frontend.

Exemples : le moteur de règles ne connaît pas le validateur XML, le moteur de rapport ne connaît
pas le validateur ZIP. Ils ne partagent que des contrats.

### Vérification automatique

Le test `backend/tests/test_architecture.py` analyse les imports de chaque module et échoue si
une de ces règles est violée. Il échoue aussi quand un nouveau module n'a pas de dépendances déclarées,
pour qu'aucun module n'échappe au contrôle. Le découplage est donc contrôlé à chaque exécution des tests et par
l'intégration continue, pas seulement documenté.

### Ajouter une règle sans modifier le moteur

Le moteur de règles (`rules/engine.py`) exécute toute classe respectant le contrat `IRule` de
`contracts/rules.py` : une méthode `evaluate(dataset)` qui renvoie une liste de `ValidationMessage`.
Une nouvelle règle est un nouveau fichier dans `rules/technical/`, déclaré dans la liste
`technical_rules()` de `rules/technical/__init__.py`, sans modification du moteur. Chaque code
qu'elle émet doit avoir son entrée dans le registre (`reference/checks/checks.json`), le catalogue
(`catalog.json`) et les textes de chaque langue : des tests vérifient l'alignement.

## 4. Frontend

```text
frontend/src/
├── api/          Appels HTTP vers le backend, un fichier par ressource
├── hooks/        État et effets réutilisables
├── components/   Composants d'affichage, sans appel réseau
├── test/         Configuration des tests
├── config.ts     Constantes (nom, version, adresse de l'API)
├── theme.ts      Thème Material UI et palette
├── App.tsx       Page d'accueil
└── main.tsx      Point d'entrée
```

Même principe de découplage : un composant n'appelle jamais `fetch` directement. Il reçoit ses
données d'un hook, qui s'appuie sur `api/`. Les types de `api/` reprennent les contrats du backend.

Le frontend n'est pas le produit : il reste une présentation mince au-dessus de l'API.

## 5. Confidentialité

Règle absolue : aucune donnée client ne quitte l'environnement du client.

| Mesure                                             | Mise en œuvre                                            |
| -------------------------------------------------- | -------------------------------------------------------- |
| Aucun appel externe                                | Pas de CDN ni d'API tierce, polices et Swagger UI embarqués dans les images, ReDoc désactivé. Contrôlé par `tests/test_docs.py` |
| Produit non exposé au réseau                       | Ports publiés sur `127.0.0.1` uniquement                 |
| Aucune persistance                                 | Pas de base de données, pas de volume Docker             |
| Aucune donnée réelle dans le dépôt                 | `.gitignore` restrictif sur `sample-data/`               |
| API exécutée sans privilèges                       | Utilisateur non root dans l'image backend                |

Règles appliquées au traitement des fichiers :

- le fichier déposé est écrit dans un dossier temporaire propre à l'import, hors volume Docker,
  supprimé avant même que la réponse soit renvoyée (`api/services/workspace.py`) ;
- les dossiers temporaires restants sont supprimés au démarrage et à l'arrêt de l'API ;
- un seul registre est conservé en mémoire : un nouvel import remplace le précédent, et le registre
  est effacé après 30 minutes sans activité (`dataset/store.py`) ;
- les journaux ne contiennent que des codes de constat et des compteurs ;
- les fichiers XML sont lus sans DTD, sans entités et sans accès réseau ;
- les archives sont contrôlées avant lecture : nombre d'entrées, taille décompressée, chemins
  dangereux, archives imbriquées.

## 6. Conventions de code

### Générales

- Code, identifiants et commentaires en anglais. Documentation du projet en français.
- Lisibilité, maintenabilité, testabilité et simplicité avant l'optimisation.
- Fins de ligne LF sur toutes les plateformes (`.gitattributes`).

### Backend

- Python 3.13, annotations de type sur toutes les fonctions publiques.
- Dépendances gérées par `uv`, verrouillées dans `uv.lock`. Pas de `pip`.
- Lint et formatage par `ruff`, lignes de 100 caractères.
- Modèles d'échange en Pydantic ou en dataclasses, placés dans `contracts`.
- Une docstring par module et par fonction publique.
- Tests avec `pytest`, fichiers `test_*.py` dans `backend/tests/`.

### Frontend

- TypeScript en mode strict, composants fonctions.
- Dépendances gérées par `npm`, verrouillées dans `package-lock.json`.
- Lint par `eslint`, formatage par `prettier`.
- Tests avec Vitest et Testing Library, fichiers `*.test.tsx` à côté du code testé.
- Aucun texte affiché n'est écrit dans un composant : tout passe par `src/i18n`.

## 7. Testabilité

- Chaque moteur dépend seulement de `contracts` : il se teste seul, avec des objets construits à la
  main, sans API ni fichier réel.
- L'API se teste avec le client de test FastAPI, sans serveur.
- Le frontend se teste en simulant les réponses de l'API.

## 8. Intégration continue

Le fichier `.github/workflows/ci.yml` exécute à chaque push et à chaque pull request :

1. backend : `ruff check`, `ruff format --check`, `pytest` ;
2. frontend : `eslint`, `prettier --check`, `vitest`, build ;
3. construction des deux images Docker.

## 9. Décisions techniques

| Décision                                         | Raison                                                        |
| ------------------------------------------------ | ------------------------------------------------------------- |
| Polars comme outil de travail, DuckDB retiré     | Polars couvre chargement CSV, contrôles et jointures. DuckDB, jamais importé, a été retiré en 0.8.5 (red team RT-25) pour réduire la surface d'attaque. |
| Frontend servi par nginx en fichiers statiques   | Image légère, comportement proche d'un déploiement réel       |
| API relayée par nginx, backend sur un réseau interne | Le backend n'a aucune route vers internet ; Swagger reste accessible sur le port 8000 |
| Swagger UI servi par l'API (`api/static/swagger-ui`) | Par défaut FastAPI le charge depuis un CDN public : contraire à la règle de confidentialité et inutilisable sans internet |
| Paquets backend à la racine de `backend/`        | Structure demandée par la spécification, imports courts (`from contracts import ...`) |
| Dockerfiles dans `docker/`, contexte à la racine | Tout l'outillage Docker au même endroit                       |
