# Références des contrôles d'identifiants (RT-08)

Red team du 28/10/2026, action RT-08. Vérifié le 31/10/2026.

Jusqu'à la 0.7.14, DAT-014, DAT-016 à DAT-021 et DAT-029 citaient une même référence, « Règles du Product Owner (issue #8) ». Ces règles n'avaient pas été vérifiées source par source (`verified: false`, sauf DAT-029). Chaque contrôle cite désormais le texte qu'il applique. **Ni les sévérités ni le comportement des contrôles ne changent.**

## 1. Sources retenues

| Contrôle | Ce qu'il vérifie | Source | Type | Clé |
|---|---|---|---|---|
| DAT-014 | La valeur a le format du type déclaré (LEI, EUID…) | ITS (UE) 2024/2956, annexe I, B_05.01.0010 : « Where LEI is used, it shall be provided as a 20-character, alpha-numeric code based on the ISO 17442 standard. Where EUID is used, it shall be provided as specified in Article 9 of the Commission Implementing Regulation (EU) 2021/1042 » | Réglementaire | `its_annex_i_b0501_0010` |
| DAT-016 | Structure de l'EUID français | Règlement d'exécution (UE) 2021/1042, annexe, point 9 (code pays, code du registre, numéro d'immatriculation) | Réglementaire | `bris_2021_1042` (existante) |
| DAT-017 | SIREN à 9 chiffres, SIRET à 14 chiffres | Service-public.fr (DILA), fiche F32135 « Comment obtenir un numéro Siren ou un Siret ? », vérifiée le 30/01/2025 : le Siren « est composé de 9 chiffres » ; le Siret « est composé de 14 chiffres : les 9 chiffres du Siren + 5 chiffres propres à chaque établissement » | Guide officiel | `dila_siren_siret` |
| DAT-018 | TVA française = FR + clé à 2 chiffres + SIREN | Service-public.fr (DILA), fiche F23570, vérifiée le 03/03/2025 : « FR + clé informatique (2 chiffres) + numéro Siren » | Guide officiel | `dila_vat_number` |
| DAT-019 | Le code supplémentaire d'une personne morale n'est ni un code national ni un passeport (depuis la 0.8.1) | ITS, annexe I, B_05.01.0040 : « LEI or EUID shall be used for legal persons, as identified in B_05.01.0070, whereas alternative code may be used only for an individual acting in a business capacity » | Réglementaire | `its_annex_i_b0501_0040` |
| DAT-020 | Le code supplémentaire diffère du code principal | **Aucune base officielle** : l'annexe I décrit B_05.01.0030 comme un « additional code […] where available », sans interdire la répétition | Produit | `po_additional_code` |
| DAT-021 | Le code d'une succursale diffère du LEI du siège | ITS, annexe I, B_01.03.0010 : « (a) LEI of the branch if unique for this branch and different from B_01.03.0020; (b) other identification code […] (where the LEI of the branch is equivalent to the one in template B_01.03.0020 or equivalent to the LEI of another branch) » | Réglementaire | `its_annex_i_b0103_0010` |
| DAT-034 | Une personne physique n'a pas d'EUID (code principal ou supplémentaire) | Règlement d'exécution (UE) 2021/1042, annexe, point 9 : l'EUID identifie les sociétés et les succursales | Réglementaire | `bris_2021_1042` (existante) |
| DAT-035 | Une personne physique déclarée avec un LEI (conseil) | **Aucune base officielle** : le GLEIF délivre des LEI aux entrepreneurs individuels ; signalé pour vérifier le type de personne | Produit | `po_sprint4_decisions` |
| DAT-029 | B_02.01.0030 cite un accord-cadre | ITS, annexe I, B_02.01.0030 « Overarching contractual arrangement reference number » : sans objet si le contrat est lui-même l'accord-cadre ou un contrat autonome | Réglementaire | `its_annex_i_b0201_0030` |

Texte de l'ITS : [EUR-Lex, JO L 2024/2956](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202402956). Fiches DILA : [F32135](https://entreprendre.service-public.gouv.fr/vosdroits/F32135), [F23570](https://entreprendre.service-public.gouv.fr/vosdroits/F23570).

## 2. Décision du PO du 31/10/2026

DAT-020 n'a pas de base officielle : son origine passe de OFFICIAL à **PO_VALIDATED** (statut PO_VALIDATED, sévérité MINOR inchangée). Les décisions produit du PO hors Sprint 3 passent de 4 à 5.

## 3. Écarts relevés, sans changement de comportement

| Contrôle | Écart | Proposition |
|---|---|---|
| DAT-019 | L'ITS est **plus strict** pour une personne morale : seuls LEI et EUID sont admis (ni CRN, ni TVA), en code principal (B_05.01.0020) comme en code supplémentaire (B_05.01.0040). À l'inverse, il admet un code alternatif (code national, passeport) pour une personne physique exerçant une activité professionnelle, ce que DAT-019 refuse toujours. La règle devrait donc dépendre du type de personne (B_05.01.0070). La pratique admise par l'EBA (CRN, TVA faute de LEI) et les observations des autorités vont dans l'autre sens | **Tranché le 02/11/2026 (A11)**, appliqué en 0.8.1 : voir `docs/dat-019-analyse.md`, §7 |
| DAT-016 | La forme française « RCS + ville du greffe + SIREN » est une pratique nationale : le règlement 2021/1042 ne fixe que la structure générale | Aucune ; l'explication du message le dit déjà |
| DAT-014 | Le conseil d'expert indique que l'EBA accepte en pratique SIREN/SIRET et TVA faute de LEI, alors que la lettre de B_05.01.0020 ne les admet pas pour une personne morale | Même arbitrage que DAT-019 |
