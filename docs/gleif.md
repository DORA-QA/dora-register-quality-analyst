# Contrôles GLEIF (version en ligne)

DORA QA existe en deux versions (décision A9 du 23/11/2026) :

- **hors ligne** : aucun code réseau ; les contrôles GLEIF sont **exclus** des constats et des
  scores, et l'écran d'accueil, la synthèse « En résumé » et les exports l'indiquent ;
- **en ligne** : les LEI du registre sont comparés à une **copie locale** des données publiques du
  GLEIF. L'analyse d'un registre reste entièrement hors ligne : seule la mise à jour de la copie,
  dans un processus séparé qui ne voit jamais de registre, va sur Internet au démarrage.

## Fonctionnement de la version en ligne

```text
DORA-QA (lanceur)
 ├─ écrit « mise à jour en cours » : aucun registre accepté (HTTP 503, écran d'attente)
 ├─ DORA-QA --gleif-update   (processus séparé, Internet)
 │    lit la dernière release « gleif-* » du dépôt public dora-qa-gleif-data
 │    vérifie les SHA-256, installe la copie dans le cache utilisateur, s'arrête
 └─ moteur + interface sur 127.0.0.1 : lisent la copie, ne vont jamais sur Internet
```

1. Au démarrage, le lanceur ferme les imports, puis lance la mise à jour dans un **processus
   séparé**. Celui-ci lit les releases du dépôt public `stephanealpha/dora-qa-gleif-data`, prend la
   plus récente et ne télécharge que si elle a changé (environ 100 Mo). Les fichiers sont vérifiés
   (SHA-256) puis installés d'un seul coup : le moteur ne voit jamais une copie à moitié écrite.
2. Tant que ce processus tourne, un fil dédié réécrit `status.json` toutes les 2 secondes, **même
   si une lecture réseau est bloquée** : le moteur répond `UPDATING` et refuse les registres.
3. **Règle stricte** « jamais connecté pendant une analyse » : chaque opération réseau expire au
   bout de 20 s, la mise à jour entière au bout de 15 min ; au-delà, le lanceur tue le processus.
   Une fois le processus terminé, plus rien ne va sur Internet.
4. En cas d'échec (pas de réseau, pare-feu), la copie déjà installée est gardée. Sans aucune copie,
   l'analyse se fait normalement et les contrôles GLEIF sont « non évalués » (GLF-010).

Emplacement de la copie (données publiques uniquement, jamais de registre) :
`%LOCALAPPDATA%\DORA-QA\gleif` (Windows), `~/Library/Caches/DORA-QA/gleif` (macOS),
`~/.cache/dora-qa/gleif` (Linux).

**Pile Docker** : le conteneur `gleif-updater` joue le rôle du processus séparé ; il est le seul à
avoir accès à Internet, le moteur reste sur un réseau interne. Version hors ligne en Docker :
`ROI_GLEIF_ENABLED=false` et retrait du service `gleif-updater`.

### Voir l'écran d'attente (recette)

`ROI_GLEIF_HOLD_SECONDS=60` garde l'état « mise à jour » le temps demandé avant de télécharger
(0 par défaut, 600 au plus).

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

Décisions des experts du projet (08/11/2026) :

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

**Chaque nuit**, dans le dépôt public de données `dora-qa-gleif-data` : workflow *GLEIF copy*
(modèle dans `tools/gleif-data-repo/`), à 02:30 UTC. Le GLEIF met à disposition la Golden Copy de
00:00 UTC à 02:00 UTC.

1. Lit la dernière Golden Copy (API `goldencopy.gleif.org/api/v2/golden-copies/publishes/latest`).
2. Ne fait rien si la release correspondante existe déjà.
3. Télécharge les fichiers XML (environ 925 Mo + 32 Mo compressés), construit les Parquet avec les
   outils de ce dépôt.
4. Refuse de publier une copie suspecte (moins de 3 millions de LEI ou 300 000 relations).
5. Publie la release `gleif-AAAAMMJJ-HHMM`, puis ne garde que les 2 dernières (2 jours).

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

- Les exceptions de niveau 2 (motif d'absence de mère) ne sont pas utilisées.
- Les noms GLEIF translittérés ne sont pas extraits : un nom en écriture locale peut donner
  GLF-007 à tort.
