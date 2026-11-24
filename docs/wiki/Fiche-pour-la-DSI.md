**Français** · [English](IT-department-sheet)

# Fiche à transmettre à votre DSI

*Page à envoyer telle quelle à votre DSI ou à votre RSSI pour demander l'autorisation d'utiliser DORA QA.*

## L'outil en bref

DORA QA (DORA Register Quality Analyst) contrôle la qualité d'un registre d'information DORA (règlement d'exécution (UE) 2024/2956, taxonomie EBA 4.0) **avant sa remise** à l'autorité. Logiciel libre sous licence **EUPL 1.2**, code source public : https://github.com/DORA-QA/dora-register-quality-analyst

## Caractéristiques techniques

| Point | Détail |
|---|---|
| Installation | Aucune : dossier portable à décompresser, **pas de droits administrateur** |
| Contenu | Exécutable PyInstaller (Python 3.13) qui embarque le moteur (FastAPI) et l'interface web (React) |
| Écoute réseau | `127.0.0.1` uniquement, port 8765 (ou un port libre) : **non joignable depuis le réseau** |
| Données du registre | Lues dans le dossier temporaire du système, **purgées** à la fin de l'analyse et à l'arrêt ; rien n'est envoyé à l'extérieur ; aucune télémétrie |
| Version **hors ligne** | **Aucun flux sortant** ; le module de téléchargement n'est pas inclus dans l'exécutable |
| Version **en ligne** | Au démarrage seulement, HTTPS sortant vers `api.github.com`, `github.com` et les domaines de téléchargement de GitHub (`*.githubusercontent.com`) pour une copie publique du GLEIF (environ 90 Mo, licence CC0) ; aucun registre accepté pendant ce téléchargement ; délai réseau de 20 s, durée maximale de 15 min |
| Cache (version en ligne) | Copie GLEIF publique dans `%LOCALAPPDATA%\DORA-QA\gleif` (Windows) ou `~/Library/Caches/DORA-QA/gleif` (macOS) ; jamais de donnée de registre |
| Exports | Créés par l'utilisateur, à sa demande ; un export « avec valeurs » contient des données du registre |
| Signature | Exécutables **non signés** (ni Authenticode, ni notarisation Apple) |
| Intégrité | Empreintes `SHA256SUMS.txt` et SBOM (SPDX) publiés avec chaque release |
| Mise à jour | Manuelle : aucune mise à jour automatique du programme |

## Options pour la DSI

- **Vérifier** l'empreinte SHA-256 et, si souhaité, auditer le code source et le SBOM.
- **Reconstruire et signer** l'outil avec le certificat de l'entreprise : [guide de signature](https://github.com/DORA-QA/dora-register-quality-analyst/blob/main/docs/signature-entreprise.md) (`signtool`, `codesign`, paquet MSI pour Intune ou SCCM).
- **Choisir la version** : hors ligne (aucun flux) ou en ligne (flux GitHub au démarrage).
- **Variante « sources »** pour les postes qui bloquent les exécutables non signés : exécution depuis VS Code avec le Python officiel (signé), bibliothèques fournies, installation hors ligne.
- **Pile Docker** pour un déploiement isolé sur serveur.

## Contact

Sécurité : signalement privé via l'onglet [Security](https://github.com/DORA-QA/dora-register-quality-analyst/security) du dépôt, ou [dora-qa@proton.me](mailto:dora-qa@proton.me) (objet « SÉCURITÉ »). Demandes confidentielles : [dora-qa@proton.me](mailto:dora-qa@proton.me).

> DORA QA est fourni « en l'état », sans garantie ; ses constats sont indicatifs et ne constituent pas une attestation de conformité.
