# Indicateurs de concentration

Sprint 3, lot 7 (brief §13, restitution §6). Version 0.7.9.

## 1. Périmètre

Ces indicateurs sont **renvoyés par l'API seulement** :
- pas d'affichage au Sprint 3 (prévu au Sprint 4) ;
- aucun effet sur le score ;
- aucun constat produit.

Ils sont calculés après les contrôles, sur le jeu de données importé, par `backend/indicators/concentration.py`. Les valeurs sont prises telles qu'elles sont déclarées, sans aucune correction ni fusion, et rien n'est écrit dans les journaux. Si le calcul échoue, l'import continue normalement : le bloc vaut `null` et seul le type de l'erreur est journalisé.

Le bloc `concentration` de la réponse de `POST /api/import` vaut `null` quand B_02.02 est absent ou vide.

## 2. Base et dimensions

**Base** : les lignes de B_02.02. Chaque ligne correspond à un service TIC fourni au titre d'un accord, pour une entité, une fonction et des lieux. Les trois tableaux utilisés sont :
- B_02.02, pour les lignes de service ;
- B_06.01, pour la criticité des fonctions ;
- B_05.01, pour le pays du siège des prestataires.

| Champ | Formule |
|---|---|
| `rows` | Nombre de lignes de B_02.02 (N) |
| `providers_count` | Nombre de prestataires directs distincts (B_02.02.0030) |
| `providers[].rows`, `share` | Lignes du prestataire (n) et part n / N, arrondie à 4 décimales |
| `providers[].code_type`, `name` | Type de code (B_02.02.0040) et nom (B_05.01.0050, `null` si le prestataire est absent de B_05.01) |
| `hhi` | Indice de Herfindahl-Hirschman : Σ (100 × n / N)², de 0 à 10 000. 10 000 = un seul prestataire. Repères usuels : moins de 1 500 = peu concentré ; plus de 2 500 = très concentré |
| `critical_functions` | Fonctions critiques ou importantes déclarées : couples (B_06.01.0010, B_06.01.0040) avec B_06.01.0050 = Oui (x28) |
| `critical_functions_without_provider` | Fonctions critiques citées par aucune ligne de B_02.02 (même constat que REL-012, sans doublon d'anomalie) |
| `providers[].critical_functions`, `critical_share` | Fonctions critiques que le prestataire soutient (fonction et entité de la ligne B_02.02), et leur part parmi les fonctions critiques soutenues. Une fonction peut reposer sur plusieurs prestataires, donc la somme des parts peut dépasser 1 |
| `single_provider_critical_functions` | Fonctions critiques soutenues par un seul prestataire direct, avec ce prestataire |
| `by_headquarters_country` | Lignes par pays du siège du prestataire (B_05.01.0080), avec le nombre de prestataires distincts (`providers`). `key = null` si le prestataire ou son pays manque |
| `by_provision_country` | Lignes par pays de fourniture du service (B_02.02.0130), `eba_GA:qx2007` (non applicable) compris |
| `by_service_type` | Lignes par type de service (B_02.02.0060, liste L08) |

Les clés sont les codes de la taxonomie (`eba_GA:FR`, `eba_TA:S14`). Les libellés seront ajoutés à l'affichage.

Chaque liste est triée par nombre de lignes décroissant, puis par code. Elle est limitée aux 50 premières valeurs, et le reste est compté dans `not_shown` (ou `providers_not_shown`, `single_provider_not_shown`).

## 3. Exemple : le golden du 29/10

- 17 lignes, 6 prestataires directs, HHI = 2 872.
- Le prestataire intragroupe porte 8 lignes, soit 47 %.
- Les deux fonctions critiques (F1 de l'entité tenant le registre, F2 du second établissement) reposent chacune sur plusieurs prestataires : aucune fonction critique ne dépend d'un prestataire unique.

## 4. Reporté

- Coût annuel par prestataire : en attente de la décision du PO sur les montants (PO-35). Le bloc le signale dans `notes`.
- Contrôles de vraisemblance et concentration géographique de la chaîne de sous-traitance : après le Sprint 3 (brief §13).
