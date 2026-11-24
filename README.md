# DORA Register Quality Analyst (DORA QA)

**Analyse locale de la qualité d'un registre d'information DORA, avant sa remise à l'autorité compétente.**
**Français** · [English](README.en.md)

DORA QA lit un registre d'information (règlement d'exécution (UE) 2024/2956, taxonomie EBA 4.0) au format **ZIP xBRL-CSV** ou dans son **enveloppe XML OneGate** (ACPR), puis produit un rapport de constats classés par gravité, avec pour chacun une explication en clair, sa référence (règle EBA, article de l'ITS, note de l'ACPR) et un conseil pour le corriger.

> ⚠️ **Avertissement.** DORA QA est un outil gratuit fourni « en l'état », sans garantie. Ses constats et conseils sont indicatifs : ils reposent sur la lecture des textes réglementaires et sur l'expérience des experts du projet, mais ne remplacent pas un avis juridique ou réglementaire et ne constituent pas une attestation de conformité opposable. Un registre sans constat peut encore être rejeté par l'autorité compétente. L'entité déclarante reste seule responsable du contenu et de la remise de son registre d'information. Le développeur décline toute responsabilité quant à l'usage des résultats.

## Confidentialité

- **Tout se passe sur votre poste.** Le registre n'est jamais envoyé sur Internet ; l'interface et le moteur ne répondent que sur `127.0.0.1`.
- **Rien n'est conservé.** Le fichier est lu dans un dossier temporaire, purgé à la fin de l'analyse et à l'arrêt de l'application.
- **Code ouvert et auditable** par vos équipes de sécurité, sous licence EUPL 1.2.

## Deux versions

| Version | Contrôles | Connexion |
|---|---|---|
| **DORA QA hors ligne** | Tous les contrôles, **sauf** ceux qui interrogent le GLEIF (l'écran l'indique) | Aucune, jamais |
| **DORA QA en ligne** | Tous les contrôles, **y compris** la vérification des LEI auprès d'une copie locale du GLEIF | Uniquement au démarrage, pour mettre à jour la copie publique du GLEIF ; aucun registre n'est accepté pendant ce téléchargement, et plus aucune connexion n'a lieu ensuite |

Choisissez la version hors ligne si votre DSI interdit toute connexion sortante.

## Installation

Téléchargez dans les [Releases](../../releases) le ZIP de votre système et de la version choisie (`DORA-QA-hors-ligne-…` ou `DORA-QA-en-ligne-…`), vérifiez son empreinte SHA-256 (fichier `SHA256SUMS.txt` de la release), décompressez-le, puis lancez :

- **Windows** : `DORA-QA.exe`. Le programme n'est pas signé : SmartScreen peut afficher « Windows a protégé votre ordinateur » ; cliquez sur *Informations complémentaires*, puis *Exécuter quand même*.
- **macOS** : `Lancer-DORA-QA.command` (ZIP `macos-arm64` pour les Mac à puce Apple, `macos-x86_64` pour les Mac Intel). L'application n'est pas notarisée : macOS la bloque. Retirez la quarantaine du dossier décompressé avec `xattr -dr com.apple.quarantine <dossier DORA-QA>` dans le Terminal (détails dans le [wiki](../../wiki/Installer-et-lancer)).
- **Linux** (x86_64, glibc 2.35 ou plus : Ubuntu 22.04, Debian 12, RHEL 9 et suivantes) : `./Lancer-DORA-QA.sh` dans un terminal.

Le navigateur s'ouvre sur l'interface. Fermez la fenêtre du terminal pour arrêter l'application.

Votre entreprise souhaite un exécutable signé à son nom ? Voir [Signer DORA QA avec votre propre certificat](docs/signature-entreprise.md) ou ouvrez une [demande de signature](../../issues/new/choose). Pour une demande confidentielle : [dora-qa@proton.me](mailto:dora-qa@proton.me).

## Ce qui est contrôlé

- **Forme du dépôt** : enveloppe XML OneGate, structure du package ZIP xBRL-CSV, nommage, encodage, fichiers attendus ou en trop.
- **Format des données** : en-têtes, types, dates, listes fermées de la taxonomie EBA, longueurs, identifiants (LEI, EUID, codes nationaux).
- **Règles de validation de l'EBA** actives pour la taxonomie 4.0, et règles d'intégrité entre tableaux.
- **Contrôles d'expert** : cohérence entre tableaux, chaîne de sous-traitance, montants, mère ultime, concentration.
- **GLEIF** (version en ligne) : existence, statut, pays et mère ultime des LEI.

Le rapport donne trois scores (réglementaire, qualité, confiance), une synthèse « En résumé », et s'exporte en CSV et JSON Lines.

## Depuis les sources

Prérequis : Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 22.

```bash
cd frontend && npm ci && npm run build && cd ..
cd backend && uv sync --frozen
uv run python ../portable/launcher.py
```

Construction des ZIP : `uv run --project backend --with pyinstaller python portable/build.py` (version hors ligne) ou `… build.py --online` (version en ligne). Sans ZIP, choisissez la version avec `DORA_QA_EDITION=online`. Une pile Docker (`docker compose up --build`) reste disponible pour un déploiement isolé sur serveur.

Guide d'utilisation pour les équipes métier : [wiki](../../wiki). Documentation technique : [architecture](docs/architecture.md), [scores](docs/scores.md), [GLEIF](docs/gleif.md), [listes fermées](docs/listes-fermees.md), [identifiants nationaux](docs/referentiel-identifiants-nationaux.md).

## Contribuer

Les signalements d'erreur et les propositions sont bienvenus : voir [CONTRIBUTING.md](CONTRIBUTING.md#français). **N'envoyez jamais de registre réel**, même partiellement : utilisez les jeux fictifs de `sample-data/`. Failles de sécurité : voir [SECURITY.md](SECURITY.md#français). Code de conduite : [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md#français).

## Contact

[dora-qa@proton.me](mailto:dora-qa@proton.me) pour les demandes confidentielles (signature entreprise, déploiement). Questions et signalements publics : [issues](../../issues/new/choose). N'envoyez jamais de registre réel, par aucun canal.

## Licence

Code publié sous **[EUPL 1.2](LICENSE)** (European Union Public Licence). Toutes les versions linguistiques officielles de la licence ont la même valeur : la version anglaise est dans [LICENSE](LICENSE), la version française dans [LICENCE.fr.txt](LICENCE.fr.txt). Données et textes de tiers : voir [NOTICE](NOTICE).

