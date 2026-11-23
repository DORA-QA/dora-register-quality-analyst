# sample-data

Jeux de données fictifs utilisés pour le développement, les tests et les démonstrations.

Règle absolue : **aucune donnée réelle de client** dans ce dossier, ni ailleurs dans le dépôt.

## Golden ROI

Le golden est un registre d'information DORA **entièrement fictif**, créé par le Product Owner pour
développer et tester l'outil. Il ne contient :

- aucune donnée client réelle ;
- aucun contrat réel ;
- aucun prestataire réel (noms du type « PSEUDO FOURNISSEUR A », « ETABLISSEMENT FINANCIER FICTIF ») ;
- aucune information confidentielle ni donnée extraite d'un registre réglementaire réel.

Ses LEI sont fictifs (inconnus du GLEIF) mais respectent la clé ISO 17442. Le package suit la
structure normalisée du registre DORA (taxonomie 4.0, xBRL-CSV), afin de tester l'import et les
contrôles du moteur.

Objectifs :

- fournir un cas nominal stable, qui passe sans aucun constat ;
- servir de référence aux tests de non-régression (`backend/tests/test_sample_data_golden.py`) ;
- servir de base aux variantes erronées générées par mutation (`backend/tests/cases/mutations.py`,
  registre `backend/tests/cases/register.csv`) ;
- tester les contrôles sans utiliser de données professionnelles réelles.

Version en vigueur : 28/10/2026 (en-têtes neutres « ROI Master Tool » dans l'enveloppe XML et dans
`report.json`, CL-29, #128). Version du 29/10/2026 : scénarios du Sprint 3 (G1 à G9, #136), décrits dans `golden-manifest.sample.json`.
Amélioration envisagée avant toute diffusion extérieure : golden reproductible par script.

Le fichier `.gitignore` ignore tout le contenu de ce dossier, sauf les fichiers nommés
`*.sample.*` et le package golden, dont le nom officiel commence par le LEI fictif
`529900P784EKW7VFMQ21` (inconnu du GLEIF).
Un registre réel déposé ici par erreur ne sera donc pas versionné.

## Fichiers fournis

| Fichier | Contenu | Résultat attendu |
| --- | --- | --- |
| `529900P784EKW7VFMQ21.CON_FR_DORA010100_DORA_2026-12-31_20261029182948489.zip` | **Golden** : package fictif complet fourni par les experts du projet (version du 29/10/2026, enrichi des scénarios G1 à G9 du Sprint 3, validé par Formalize), copie de `backend/tests/golden/golden.sample.zip`. Garder ce nom : il est contrôlé (PKG-002, PKG-016, PKG-021) | `SUCCESS_WITH_WARNINGS`, seuls les constats admis par le manifeste : 2 MINOR REL-007 (art. 3 §5), 1 INFO DQ-006 (accord terminé, G7) et 5 MINOR REL-017 (stratégie de sortie) ; 15 tables, 107 lignes |
| `golden-manifest.sample.json` | Manifeste du golden : scénarios couverts (G1 à G9, où les trouver) et constats admis, aujourd'hui et après le Sprint 3 | Vérifié par `backend/tests/test_sample_data_golden.py` |
| `golden-onegate.sample.xml` | Le golden dans son enveloppe OneGate | Comme le golden |
| `onegate-envelope-valid.sample.xml` | Petit package valide dans une enveloppe OneGate | `SUCCESS`, 15 tables ; une information DQ-004 (prestataires sans accord : ce package n'est pas un registre complet) |
| `package-with-defects.sample.zip` | Modèle manquant, fichier Excel en trop, BOM, mauvais séparateur, indicateur en majuscules | `FAILED` |
| `package-with-data-defects.sample.zip` | Package bien formé dont les données cassent les règles techniques : colonne inconnue, clé primaire vide, clé en double, référence à un contrat inexistant, LEI à clé de contrôle invalide, EUID de syntaxe incorrecte ou hors EEE | `FAILED` (DAT-001, 003, 004, 005, 010, 011, 012) |
| `onegate-envelope-with-defects.sample.xml` | Le package défectueux, avec un LEI d'expéditeur et un domaine incorrects | `FAILED` |
| `package-multi-defects.sample.zip` | **Package multidéfauts du Sprint 3** : le golden avec une mutation par famille de contrôles (entités, prestataires, accords, fonctions, chaînes, listes fermées), appliquées ensemble | `FAILED` ; codes, nombres de constats et d'occurrences fixés par son manifeste |
| `package-multi-defects.manifest.sample.json` | Manifeste du package multidéfauts : mutations appliquées, constats attendus, exceptions expliquées | Vérifié par `backend/tests/test_sample_data_golden.py` |

Les fichiers golden sont fournis par le PO ; les autres sont générés par `backend/tests/make_samples.py`. Les tableaux utilisent les colonnes officielles de la taxonomie 4.0 ; les valeurs sont inventées.

## Identifiants réels dans les tests (red team RT-16)

Les tests de la clé de contrôle ISO 17442 (`backend/tests/test_identifiers.py`) et certaines mutations
(`LEI_OTHER`) utilisent trois LEI **réels et publics**, choisis parce que leur clé est connue juste :
`5493001KJTIIGC8Y1R12` (Bloomberg Finance L.P.), `7ZW8QJWVPR4P1J1KQY45` (Google LLC) et
`HWUPKR0MPOU8FGXBT394` (Apple Inc.), tous actifs selon GLEIF. Ce sont des données publiques de GLEIF,
gardées par décision du PO (31/10/2026). Leurs variantes à clé faussée (`…R13`) servent de cas invalides.
