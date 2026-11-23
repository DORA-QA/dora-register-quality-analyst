# Provenance du référentiel des règles de validation de l'EBA

Issue #127 (CL-28), red team RT-11. Mis à jour le 31/10/2026, version 0.7.14.

`backend/reference/dora/rule-status-4.0.json` contient les **71 règles de validation DORA** de l'EBA et leur état : **49 actives, 22 inactives**. Seules les règles actives produisent des constats (décision PO-1 du 18/10). Jusqu'au 30/10, ce fichier était tiré de `docs/sources/CONF-ReglesEBA.xlsx`, un export tiers qui contenait trois colonnes propres à l'outil d'origine. L'export est retiré du dépôt : le référentiel est désormais reconstruit **depuis les seules sources publiques de l'EBA**.

## 1. Sources

| Rôle | Fichier | Publication | Empreinte SHA-256 | Dans le dépôt |
|---|---|---|---|---|
| **Règles et état** | [VR_4.4.phase1_.xlsx](https://www.eba.europa.eu/sites/default/files/2026-10/4c299b8b-c5ee-482d-b26d-454be40b129b/VR_4.4.phase1_.xlsx), feuille `VR_4.4.phase1`. Lien « (from 4.0) EBA_Validation rules » de la page [Validation rules packages](https://www.eba.europa.eu/risk-and-data-analysis/reporting/reporting-frameworks/validation-rules-packages) | Octobre 2026 (modifié par l'EBA le 12/10/2026) ; téléchargé le 31/10/2026 | `38c190fa4c2ff81f22a5bd2ed94f744fc64e4eb9b722676e07f89669d79b1aea` | Oui : `backend/reference/dora/sources/eba-validation-rules-4.4-phase1-2026-10.xlsx` (1,1 Mo) |
| Désactivations (recoupement) | [Micro taxonomy package](https://www.eba.europa.eu/sites/default/files/2026-09/b39346c3-8a83-4692-9839-104ca1612914/Micro_taxonomy_package.zip) 4.3.0.1 (petit paquet de validation du 14/09/2026), `set/dora-ignore-val.xml` de la version 4.0 | 14/09/2026 ; téléchargé le 31/10/2026 | `ea6184a7e3a67016346f2154bfb04ca0a489ea829cf344239367fa216d21709f` | Non : recoupement seulement |
| Règles présentes dans la taxonomie | Taxonomie XBRL de l'EBA 4.0 (errata 5) : voir `enumerations-4.0.provenance.json`, rôle « codes » | 20/03/2025 | `27f3a44a6bdef56a7daf2114778707604c20b258e4466d5ebfb5c37b7598bad2` | Non : 106 Mo, gardée par le PO |

Le détail lisible par une machine est dans `backend/reference/dora/rule-status-4.0.provenance.json`.

## 2. Transformations (`backend/tools/build_rule_status.py`)

Le script n'utilise que la bibliothèque standard de Python et ne télécharge rien. Il vérifie d'abord l'empreinte de la liste, puis :

1. Il ne garde que les lignes dont la colonne `Frameworks` vaut `DORA` : 71 règles sur 14 164.
2. Il reprend telles quelles les colonnes de l'EBA suivantes :

   | Colonne de l'EBA | Champ du référentiel | Remarque |
   |---|---|---|
   | `VR Code` | `id` | |
   | `Tables` | `table` | |
   | `Source` | `type` | `existence`, `sign` ou `user_defined` |
   | `Severity` | `severity` | |
   | `IsActive` | `active` | |
   | `Expression` | `expression` | espaces normalisés |

3. Il calcule `cells`, la liste des colonnes citées par l'expression (`c0010`, `c0020-0090`, `c*`), dans leur ordre d'apparition. Le moteur s'en sert de garde-fou : une règle n'est interprétée que si ses colonnes sont exactement celles-là.
4. Il calcule `in_taxonomy`, qui dit si la règle figure dans `validation-rules-4.0.json` (la taxonomie). Il vérifie que cette valeur concorde avec la colonne `Implemented in XBRL` de l'EBA.

```
cd backend
python -I tools/build_rule_status.py            # vérifie : reconstruit et compare (code 1 en cas d'écart)
python -I tools/build_rule_status.py --write    # réécrit rule-status-4.0.json
```

Le test `backend/tests/test_rule_status_provenance.py` refait ces vérifications à chaque exécution de la CI. Il contrôle l'empreinte, la reconstruction à l'identique, les comptes et l'absence de l'export retiré.

## 3. Recoupements du 31/10/2026

| Comparaison | Résultat |
|---|---|
| Liste officielle `VR_4.4.phase1` / référentiel issu de l'export (liste du 14/09/2026) | **Identiques** règle par règle : 71 identifiants, tableau, type, sévérité, état, expression |
| `cells` calculé / `cells` de l'export | Identiques pour les 71 règles |
| Micro taxonomy package du 14/09/2026 | Il désactive 15 règles : ce sont exactement les 15 règles inactives présentes dans la taxonomie XBRL. Les 7 autres règles inactives (v8823, v8824, v8893 à v8897) ne sont pas implémentées en XBRL |
| Taxonomie 4.0 (mars 2025) | Elle contient 61 des 71 règles. Les 10 absentes (v8823, v8824, v8890 à v8897) sont celles marquées `Implemented in XBRL = No`. Elle ne désactive que 6 règles : c'est l'état de mars 2025, d'où le choix de la liste de l'EBA comme source de l'état |

## 4. Mise à jour

À chaque nouvelle liste de l'EBA :
1. Remplacer le fichier de `backend/reference/dora/sources/`.
2. Mettre à jour l'URL, la date et l'empreinte dans `rule-status-4.0.provenance.json`.
3. Lancer `build_rule_status.py --write`.
4. Lire le diff : une règle qui change d'état modifie les constats produits.
5. Si l'état d'une règle change, le soumettre au PO.
