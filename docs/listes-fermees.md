# Listes fermées : provenance, concordance et contrôle DAT-033

Sprint 3, lot 6 (#133, #153, RT-08, RT-12). Version 0.7.8.

## 1. D'où viennent les listes

| Rôle | Source | Publication | Empreinte SHA-256 | Statut |
|---|---|---|---|---|
| **Codes** (valeurs autorisées) | Taxonomie XBRL de l'EBA 4.0, module DORA (`AllowedValue` de chaque tableau), lue par `backend/tools/build_reference.py` | 20/03/2025 ([page EBA](https://www.eba.europa.eu/risk-and-data-analysis/reporting-frameworks/reporting-framework-40)), téléchargée le 31/10/2026 (106 Mo, hors dépôt) | `27f3a44a6bdef56a7daf2114778707604c20b258e4466d5ebfb5c37b7598bad2` | **Vérifiée** : empreinte calculée deux fois ; `build_reference.py`, relancé sur `Full_Taxonomy.7z`, régénère à l'identique les quatre référentiels du dépôt (colonnes, champs, listes, règles de validation) (PO-37, #153) |
| **Libellés** | Classeur de l'EBA « List of possible values for all data fields with drop downs (updated 3 March 2025) », copie dans `backend/reference/dora/sources/` | 03/03/2025, téléchargé le 30/10/2026 | `a0fed557cc6837f909227088338408581cd413cce046566dcc7b4253ba009c9f` | **Vérifiée** : empreinte donnée par le PO, recalculée (#153) |

Le détail (URL complètes, dates, statut) est dans `backend/reference/dora/enumerations-4.0.provenance.json`.

**Décision P4** : la taxonomie fait foi. Le classeur sert aux libellés et au contrôle de concordance, jamais à ajouter ou retirer un code.

## 2. Vérification reproductible

```
cd backend
python -I tools/build_enumerations.py            # vérifie l'empreinte et la concordance
python -I tools/build_enumerations.py --labels   # réécrit aussi les libellés depuis le classeur
```

Le script ne télécharge rien et n'utilise que la bibliothèque standard de Python. Il renvoie le code 1 :
- si l'empreinte du classeur diffère ;
- ou si une liste du classeur ne correspond à aucune liste de `enumerations-4.0.json`, une fois les écarts documentés appliqués.

Le test `backend/tests/test_closed_lists.py` fait les mêmes vérifications à chaque exécution de la CI. Il vérifie aussi que chaque écart documenté existe encore. Quand l'EBA publiera une nouvelle version, il faudra :
1. remplacer le classeur ;
2. mettre à jour l'empreinte ;
3. relancer le script ;
4. retirer les écarts disparus.

## 3. Concordance entre le classeur et la taxonomie

Les 21 listes de la taxonomie (L01 à L21) servent à 41 champs. Le classeur compte 33 colonnes de valeurs réparties sur 11 onglets.

| Constat | Détail | Décision |
|---|---|---|
| 19 listes identiques | Toutes sauf L05 et L10. Plusieurs colonnes du classeur reprennent la même liste : B_07.01.0080 = L11, B_07.01.0100 = L18, B_07.01.0110 = L17 | — |
| **L05, devises** | Le classeur contient `eba_CU:HRK` (kuna croate, remplacée par l'euro le 1er janvier 2023). La taxonomie ne la contient pas : 166 devises | Décision du PO du 30/10/2026 : la taxonomie prévaut (P4). Une valeur HRK sort de la liste et lève DAT-033 |
| **L10, pays et « non applicable »** | L'onglet B0202 du classeur compte 248 pays : CW, DJ, DM et DO manquent alors qu'ils figurent sur tous les autres onglets. `eba_GA:qx2007` (non applicable) n'est autorisé que pour B_02.02.0130, 0150 et 0160 | Le classeur est tronqué, on conserve la liste L10 de la taxonomie |
| **L07, type de code** (RT-08) | La taxonomie énumère LEI (qx2000), code national (qx2001), EUID (qx2002), CRN (qx2003), TVA (qx2004) et passeport (qx2005). Le texte rectifié de l'ITS (19/09/2025) énumère LEI, EUID, CRN, TVA, PNR et NIN | P4 : la taxonomie fait foi. Les messages de DAT-014 et DAT-016 à DAT-021 emploient déjà les termes de la taxonomie (code national, passeport) |

## 4. Le contrôle DAT-033

- **Portée** : toute valeur non vide des 41 champs à liste fermée doit être un code de sa liste, écrit exactement (préfixe, casse, sans espace). Les valeurs vides relèvent des contrôles de champs obligatoires.
- **Sévérité** : MAJOR, origine OFFICIAL (P3). Le statut est **provisoire** : aucun code de rejet des autorités n'est connu pour ce cas.
- **Restitution** : un constat par tableau et par colonne, avec la liste en cause (L01 à L21) et chaque occurrence (ligne, valeur). Le bon code n'est proposé que s'il est certain : même code avec une autre casse ou des espaces, ou libellé exact de la liste (« High » → `eba_ZZ:x793`).
- **Golden** : le golden du 29/10 est conforme sur les 41 champs et ne lève pas DAT-033.

## 5. Reste à faire

- RT-12 : fait le 31/10/2026 (PO-37). L'empreinte de l'archive de la taxonomie est consignée, et le référentiel entier a été régénéré à l'identique depuis elle.
- RT-08 : fait le 31/10/2026. Chaque contrôle d'identifiant cite sa source officielle (`docs/sources/identifiants-references.md`) ; les écarts entre l'ITS et DAT-019 sont soumis au PO.
