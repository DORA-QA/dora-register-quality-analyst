**Français** · [English](Install-and-start)

# Installer et lancer DORA QA

> ⚠️ Sur un **poste de l'entreprise**, faites ces étapes **avec l'accord de votre DSI** (voir [Autonomie et DSI](Autonomie-et-DSI)). Votre DSI peut aussi vous fournir directement une version déjà vérifiée et signée.

DORA QA ne s'installe pas : c'est un dossier à décompresser. Aucun droit d'administrateur n'est nécessaire.

## 1. Télécharger

1. Ouvrez la page [Releases](https://github.com/DORA-QA/dora-register-quality-analyst/releases) du projet.
2. Dans la dernière version, téléchargez le ZIP de votre système et de votre version :
   - Windows : `DORA-QA-hors-ligne-…-windows-amd64.zip` (ou `en-ligne`) ;
   - Mac à puce Apple (M1 et suivants) : `DORA-QA-hors-ligne-…-macos-arm64.zip` (ou `en-ligne`) ;
   - Mac Intel (modèles plus anciens) : `DORA-QA-hors-ligne-…-macos-x86_64.zip` (ou `en-ligne`) ;
   - Linux (x86_64, Ubuntu 22.04, Debian 12, RHEL 9 ou plus récent) : `DORA-QA-hors-ligne-…-linux-x86_64.zip` (ou `en-ligne`).

   *Puce Apple ou Intel ?* Menu Pomme > *À propos de ce Mac* : la ligne « Puce » indique Apple M…, la ligne « Processeur » indique Intel.
3. *(Recommandé, ou à faire par la DSI)* comparez l'empreinte du fichier avec celle du fichier `SHA256SUMS.txt` de la même page.

## 2. Décompresser

Il n'y a **qu'un seul ZIP** à décompresser.

- **Windows** : clic droit sur le ZIP > *Extraire tout…* > *Extraire*. Ne lancez jamais le programme depuis l'intérieur du ZIP : Windows l'ouvre comme un dossier, mais le programme n'y fonctionne pas.
- **Mac** : double-cliquez sur le ZIP.
- **Linux** : `unzip DORA-QA-…-linux-x86_64.zip` dans un terminal (ou le gestionnaire d'archives).

Choisissez un dossier simple, par exemple `Documents`. Vous obtenez un dossier au nom du ZIP qui contient le dossier **`DORA-QA`** : c'est dans ce dernier que se trouve le programme.

```
DORA-QA-hors-ligne-1.0.0-windows-amd64\
└── DORA-QA\
    ├── DORA-QA.exe          ← à lancer (Windows)
    ├── LICENSE.txt, NOTICE.txt
    └── …
```

> ℹ️ **Versions de test** (recette, avant publication) : le ZIP se télécharge depuis la page d'une exécution du workflow *Release*, rubrique *Artifacts*. Il s'agit du même ZIP, à décompresser une seule fois. Les versions de test produites avant la version 1.0.0 étaient emballées dans un second ZIP : il fallait alors décompresser deux fois.

## 3. Lancer

- **Windows** : double-cliquez sur `DORA-QA.exe`.
  - Si Windows affiche « Windows a protégé votre ordinateur » : c'est l'alerte attendue pour un programme non signé. **Sur un poste professionnel, demandez à votre DSI.** Sur un ordinateur personnel : *Informations complémentaires* > *Exécuter quand même*.
- **Linux** : dans un terminal, depuis le dossier `DORA-QA`, lancez `./Lancer-DORA-QA.sh`.
- **Mac** : double-cliquez sur `Lancer-DORA-QA.command`.
  - La première fois, macOS le bloque. **Sur un Mac professionnel, demandez à votre DSI.** Sur un Mac personnel : *Réglages Système* > *Confidentialité et sécurité* > *Ouvrir quand même* en face de DORA QA, puis relancez.

Une fenêtre noire (terminal) s'ouvre : **ne la fermez pas**, c'est le moteur de l'outil. Le navigateur s'ouvre ensuite tout seul sur DORA QA.

## 4. Accepter l'avertissement

À chaque lancement, une fenêtre rappelle que l'outil est fourni « en l'état », sans garantie, et que ses constats sont indicatifs. Cochez la case, puis cliquez sur **Continuer**.

## 5. Arrêter

Fermez la fenêtre du terminal. Le registre analysé est effacé et les fichiers temporaires sont supprimés.
