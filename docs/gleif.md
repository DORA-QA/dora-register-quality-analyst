# Contrôles GLEIF (branche `feature/gleif-local`)

Les LEI du registre sont comparés à une **copie locale** des données du GLEIF. L'analyse d'un
registre reste entièrement hors ligne : seul un petit conteneur de mise à jour, qui ne voit jamais
de registre, va sur Internet au démarrage.

## Fonctionnement

```text
docker compose up
 ├─ gleif-updater  (réseau « default », Internet)        ─┐
 │    lit la dernière release « gleif-* » du dépôt        │ volume gleif-data
 │    vérifie les SHA-256, installe la copie, s'arrête    │ (données publiques GLEIF)
 ├─ backend        (réseau interne, sans Internet) ◄──────┘ lecture seule
 └─ frontend       (seule porte, 127.0.0.1)
```

1. Au démarrage, `gleif-updater` lit les releases du dépôt dont le tag commence par `gleif-`,
   prend la plus récente, compare son `manifest.json` à la copie installée et ne télécharge que si
   elle a changé (environ 100 Mo). Les fichiers sont vérifiés (SHA-256) puis installés d'un seul
   coup (renommage du dossier) : le backend ne voit jamais une copie à moitié écrite.
2. Pendant le téléchargement, il réécrit `status.json` toutes les 2 secondes. Le backend répond
   `UPDATING` sur `GET /api/gleif/status` et **refuse les registres** (HTTP 503).
3. La page affiche un **écran d'attente** (« Mise à jour en ligne en cours… Il ne peut pas
   accepter de registre pour l'instant ») avec la progression, puis se ferme toute seule.
4. En cas d'échec (pas de réseau, pas d'accès au dépôt), la copie déjà installée est gardée. Sans
   aucune copie, l'analyse se fait normalement et les contrôles GLEIF sont « non évalués »
   (GLF-010). Un conteneur de mise à jour silencieux plus de 60 s ne bloque plus l'outil.

### Voir l'écran d'attente (recette)

Avec une bonne connexion, la copie (environ 100 Mo) est souvent installée avant que la page ne
s'ouvre. Pour vérifier l'écran, la variable `ROI_GLEIF_HOLD_SECONDS` garde l'état « mise à jour »
le temps demandé avant de télécharger (0 par défaut, 600 au plus) :

```bash
ROI_GLEIF_HOLD_SECONDS=60 docker compose up --build
```

### Dépôt privé

Tant que le dépôt est privé, le conteneur a besoin d'un jeton GitHub en lecture seule :

```bash
export ROI_GLEIF_TOKEN=github_pat_...   # jeton « fine-grained », droit Contents: Read-only
docker compose up --build
```

Le jeton n'est passé qu'au conteneur `gleif-updater`, jamais au backend ni au navigateur.

## Contrôles

| Code | Contrôle | Sévérité | Origine |
|---|---|---|---|
| GLF-001 | LEI introuvable dans le GLEIF (EBA VR_2, VR_12, VR_23, VR_71, VR_77) | MAJOR (warning EBA) | OFFICIAL |
| GLF-002 | LEI non valide : RETIRED, MERGED, ANNULLED, DUPLICATE, PENDING_* ou entité INACTIVE ; successeur indiqué | MAJOR | OFFICIAL (ITS art. 3 §5) |
| GLF-003 | LEI non renouvelé (LAPSED) | MINOR | OFFICIAL (ITS art. 3 §5 ; FAQ EBA Q44) |
| GLF-004 | Renouvellement dû avant le 30 avril suivant la date d'arrêté | INFO | DATA_QUALITY |
| GLF-005 | Pays de B_01.02.0030 différent du GLEIF (EBA VR_16) | MAJOR (warning EBA) | OFFICIAL |
| GLF-006 | Pays de B_01.01.0030 ou B_05.01.0080 différent du GLEIF | MINOR | DATA_QUALITY |
| GLF-007 | Nom différent du nom légal GLEIF | MINOR | DATA_QUALITY |
| GLF-008 | Mère directe (B_01.02.0060) différente du GLEIF | MINOR | DATA_QUALITY |
| GLF-009 | Mère ultime (B_05.01.0110) de chaque prestataire identifié par LEI différente du GLEIF (vide ou typée autrement que LEI comprises) | MINOR | DATA_QUALITY |
| GLF-010 | Aucune copie GLEIF installée (contrôles non évalués) | INFO | TECHNICAL |
| GLF-011 | Copie GLEIF de plus de 7 jours | INFO | TECHNICAL |

Chaque constat cite la date de la copie GLEIF utilisée. Seuls les LEI bien formés sont recherchés
(le format relève de DAT-006 à DAT-010). Les pays sont comparés à l'adresse légale **et** au siège
GLEIF : l'EBA ne dit pas lequel VR_16 utilise.

Décisions du PO (08/11/2026) :

- source : **Golden Copy** du GLEIF (sans doublons techniques), et non les fichiers concaténés ;
- DUPLICATE, ANNULLED et tous les statuts PENDING_* sont **non valides** (GLF-002) ;
- pour **chaque ligne de B_05.01 dont 0010 est un LEI**, la mère ultime 0110 doit être celle du
  GLEIF (GLF-009) ; non contrôlé quand le GLEIF n'enregistre pas de mère ultime (les exceptions
  de niveau 2 ne sont pas utilisées).

**Date d'appréciation du statut** : l'EBA vérifie les LEI contre son propre cache du GLEIF quand
elle traite le registre (après la remise, contrôles qualité d'avril en 2026), pas à la date
d'arrêté. L'outil apprécie donc le statut à la date de la copie installée et signale en plus
(GLF-004) les renouvellements dus avant la fin probable de ce traitement.

## Publier une nouvelle copie

**Chaque nuit** : workflow *GLEIF copy* (`.github/workflows/gleif-copy.yml`), à 02:30 UTC
(03:30 à Paris l'hiver, 04:30 l'été ; GitHub ne connaît que l'heure UTC). Le GLEIF met à
disposition la Golden Copy de 00:00 UTC à 02:00 UTC.

1. Lit la dernière Golden Copy (API `goldencopy.gleif.org/api/v2/golden-copies/publishes/latest`).
2. Ne fait rien si la release correspondante existe déjà.
3. Télécharge les fichiers XML (environ 925 Mo + 32 Mo compressés), construit les Parquet.
4. Refuse de publier une copie suspecte (moins de 3 millions de LEI ou 300 000 relations).
5. Publie la release `gleif-AAAAMMJJ-HHMM`, puis ne garde que les 7 dernières.

Lancement manuel possible (Actions › GLEIF copy › Run workflow, option « force »). GitHub n'exécute
les tâches planifiées que depuis la branche par défaut : le fichier doit être sur `main` (il
construit avec les outils de `feature/gleif-local` tant que la branche n'est pas fusionnée).

**À la main**, à partir des fichiers XML du GLEIF (LEI-CDF et RR-CDF, Golden Copy ou Concatenated
Files, en ZIP ou décompressés) :

```bash
cd backend
uv run python -m tools.build_gleif --lei <lei2.xml|.zip> --rr <rr.xml|.zip> --out gleif-release
tools/publish_gleif_release.sh gleif-release     # tag gleif-AAAAMMJJ-HHMM
```

Mesures sur les fichiers du 08/11/2026 (11,6 Go de XML) : lei.parquet 90 Mo, rr.parquet 8 Mo ;
environ 8 minutes sur un cœur ; recherche de 5 000 LEI en 0,15 s.

## Limites connues

- Le ZIP portable Windows (branche `demo/portable`) n'a pas de conteneur de mise à jour : ces
  contrôles n'y sont pas branchés.
- Les exceptions de niveau 2 (motif d'absence de mère) ne sont pas utilisées.
- Les noms GLEIF translittérés ne sont pas extraits : un nom en écriture locale peut donner
  GLF-007 à tort.
