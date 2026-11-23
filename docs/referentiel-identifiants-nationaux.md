# Référentiel des identifiants nationaux (hors LEI et EUID)

19 octobre 2026 · Claude · issue #41 · fichier `backend/reference/dora/national-identifiers.json`

Formats des numéros de **TVA** et des **numéros d'immatriculation** (CRN) pour les 27 pays de l'UE, l'Irlande du Nord (XI), le Royaume-Uni et la Suisse. **Le référentiel est branché sur DAT-017 (immatriculation) et DAT-018 (TVA)** pour les pays dont tous les formats sont CONFIRMED (décision du PO, issue #41) ; la France garde ses règles propres. Les autres pays (formats A_VERIFIER) ne sont pas contrôlés : une recherche de formats se poursuit, en priorité pour les pays fournisseurs de services IT.

## Statuts

- **CONFIRMED** : format lu sur une source officielle (absolue ou fiable, voir `docs/methode.md`).
- **A_VERIFIER** : format connu de Claude, **non vérifié** ; ne doit servir à aucun contrôle bloquant avant confirmation.

Les formats de TVA sont tous CONFIRMED : deux sources concordantes (EUIPO, europa.eu, et l'administration fiscale finlandaise), plus l'AFC pour la Suisse.

## Synthèse

| Pays | TVA | Numéro d'immatriculation | Statut CRN |
| --- | --- | --- | --- |
| AT Autriche | ATU + 8 chiffres | Firmenbuchnummer : jusqu'à 6 chiffres + 1 lettre (préfixe FN facultatif) | CONFIRMED |
| BE Belgique | BE + 10 chiffres (commence par 0 ou 1) | Numéro d'entreprise BCE/KBO : 10 chiffres, commence par 0 (anciens) ou 1 (depuis le 19/09/2023), points facultatifs | CONFIRMED |
| BG Bulgarie | BG + 9 ou 10 chiffres | EIK (UIC) : 9 ou 13 chiffres | A_VERIFIER |
| HR Croatie | HR + 11 chiffres | OIB : 11 chiffres | A_VERIFIER |
| CY Chypre | CY + 8 chiffres + 1 lettre | Numéro d'enregistrement : HE + jusqu'à 6 chiffres (sociétés) | A_VERIFIER |
| CZ Tchéquie | CZ + 8 à 10 chiffres | IČO : 8 chiffres | A_VERIFIER |
| DK Danemark | DK + 8 chiffres | CVR : 8 chiffres | A_VERIFIER |
| EE Estonie | EE + 9 chiffres | Registrikood : 8 chiffres | A_VERIFIER |
| FI Finlande | FI + 8 chiffres | Y-tunnus (Business ID) : 7 chiffres, un tiret, 1 chiffre de contrôle | CONFIRMED |
| FR France | FR + 2 caractères (clé) + SIREN | SIREN : 9 chiffres ; SIRET : 14 chiffres (SIREN + NIC) | CONFIRMED |
| DE Allemagne | DE + 9 chiffres | Registernummer : section du registre (HRA, HRB…) + numéro ; pas de numéro national unique, le tribunal du registre est nécessaire | A_VERIFIER |
| GR Grèce | EL (et non GR) + 9 chiffres | Numéro GEMI : 12 chiffres ; AFM (numéro fiscal) : 9 chiffres | A_VERIFIER |
| HU Hongrie | HU + 8 chiffres | Cégjegyzékszám : 10 chiffres (cour – forme – numéro) | A_VERIFIER |
| IE Irlande | IE + 8 ou 9 caractères | Numéro CRO : numérique | CONFIRMED |
| IT Italie | IT + 11 chiffres | Codice fiscale / Partita IVA : 11 chiffres (identiques pour les sociétés) ; Numéro REA : sigle de province + numéro | CONFIRMED |
| LV Lettonie | LV + 11 chiffres | Numéro d'enregistrement : 11 chiffres | A_VERIFIER |
| LT Lituanie | LT + 9 ou 12 chiffres | Juridinio asmens kodas : 9 chiffres | A_VERIFIER |
| LU Luxembourg | LU + 8 chiffres | Numéro RCS : lettre de section (B pour les sociétés commerciales) + numéro | A_VERIFIER |
| MT Malte | MT + 8 chiffres | Numéro d'enregistrement : C + numéro | A_VERIFIER |
| NL Pays-Bas | NL + 9 chiffres + B + 2 chiffres | KVK-nummer : 8 chiffres | CONFIRMED |
| PL Pologne | PL + 10 chiffres (NIP) | REGON : 9 chiffres (unité juridique) ou 14 (unité locale) ; KRS : 10 chiffres ; NIP : 10 chiffres | A_VERIFIER, CONFIRMED |
| PT Portugal | PT + 9 chiffres | NIPC : 9 chiffres | A_VERIFIER |
| RO Roumanie | RO + 2 à 10 chiffres | CUI : 2 à 10 chiffres ; Numéro ONRC : ancien format J40/1234/2010, nouveau format J + 13 chiffres | A_VERIFIER |
| SK Slovaquie | SK + 10 chiffres | IČO : 8 chiffres | A_VERIFIER |
| SI Slovénie | SI + 8 chiffres | Matična številka : 7 ou 10 chiffres | A_VERIFIER |
| ES Espagne | ES + 9 caractères (première ou dernière position alphabétique) | NIF (personne morale) : lettre de forme juridique + 7 chiffres + caractère de contrôle | CONFIRMED |
| SE Suède | SE + 10 chiffres + 01 | Organisationsnummer : 10 chiffres (NNNNNN-NNNN) | A_VERIFIER |
| XI Irlande du Nord (TVA UE pour les biens) | XI + 9 ou 12 chiffres (ou GD/HA + 3 chiffres) | – | – |
| GB Royaume-Uni | GB + 9 ou 12 chiffres (ou GD/HA + 3 chiffres) | Companies House number : 2 lettres + jusqu'à 6 caractères, ou jusqu'à 8 chiffres | CONFIRMED |
| CH Suisse | UID + MWST, TVA ou IVA (VAT n'est pas admis) | UID : CHE + 9 chiffres (CHE-123.456.789) | CONFIRMED |

## Points d'attention

1. **TVA française** : les sources européennes admettent une clé de 2 **caractères** (lettres possibles), service-public.gouv.fr parle de 2 **chiffres**. DAT-018 n'accepte toujours que des chiffres pour la France : risque de fausse alerte sur une clé alphanumérique (rare). Décision à prendre.
2. **Allemagne** : pas de numéro national unique ; le numéro du registre (HRA, HRB…) n'a de sens qu'avec le tribunal du registre. Un contrôle de format y serait faible.
3. **Royaume-Uni** : les numéros GB ne sont plus dans VIES depuis 2021 ; le préfixe XI (Irlande du Nord) reste valable pour les biens jusqu'au 31/12/2028.
4. **Grèce** : code pays GR dans les listes EBA, mais préfixe **EL** dans le numéro de TVA (déjà géré pour l'EUID).
5. **22 formats d'immatriculation restent A_VERIFIER** (BG, HR, CY, CZ, DK, EE, DE, GR, HU, LV, LT, LU, MT, PL KRS/NIP, PT, RO, SK, SI, SE) : sites officiels inaccessibles depuis l'environnement (protection anti-robots) ou format non précisé.

## Sources

- [EUIPO (europa.eu), « VAT numbers EU », tableau des formats de TVA](https://euipo.europa.eu/tunnel-web/secure/webdav/guest/document_library/Documents/COSME/VAT%20numbers%20EU.pdf) — référence absolue
- [Administration fiscale finlandaise (vero.fi), « VAT numbers issued by different EU countries », mise à jour du 17/01/2025](https://www.vero.fi/en/businesses-and-corporations/taxes-and-charges/vat/international-commerce/vat-number/vat-numbers-issued-by-different-eu-countries/) — référence fiable
- [service-public.gouv.fr, numéro de TVA intracommunautaire (FR + clé 2 chiffres + SIREN)](https://entreprendre.service-public.gouv.fr/vosdroits/F23570) — référence absolue
- [annuaire-entreprises.data.gouv.fr, SIREN et SIRET](https://annuaire-entreprises.data.gouv.fr/definitions/numero-siret) — référence absolue
- [SPF Économie (economie.fgov.be), « Les numéros d'entreprise passent au 1 » : 10 chiffres, 0 puis 1 depuis le 19/09/2023](https://news.economie.fgov.be/228779-les-numeros-d-entreprise-passent-au-1/) — référence fiable
- [KVK (kvk.nl), « KVK number: all you need to know » : 8 chiffres](https://www.kvk.nl/en/about-the-business-register/kvk-number-all-you-need-to-know/) — référence fiable
- [Justiz (justiz.gv.at), aide Firmenbuchnummer : jusqu'à 6 chiffres et une lettre (ex. 123456b)](https://edikte.justiz.gv.at/edikte/ex/edparm3.nsf/h/IDHLf01!OpenDocument) — référence fiable
- [YTJ (ytj.fi), Business ID : 7 chiffres, un tiret, un chiffre de contrôle](https://www.ytj.fi/en/index/businessid.html) — référence fiable
- [BOE, Orden EHA/451/2008, art. 2 : NIF des personnes morales sur 9 caractères](https://www.boe.es/buscar/act.php?id=BOE-A-2008-3580) — référence fiable
- [Registro Imprese (registroimprese.it) : codice fiscale = partita IVA pour les sociétés ; REA = sigle de province + numéro](https://www.registroimprese.it/codice-fiscale-p.iva-rea) — référence fiable
- [GUS (stat.gov.pl) : REGON 9 chiffres (unité juridique) ou 14 (unité locale)](https://stat.gov.pl/metainformacje/slownik-pojec/pojecia-stosowane-w-statystyce-publicznej/2963,pojecie.html) — référence fiable
- [AFC (estv.admin.ch), UID : CHE-123.456.789 ; numéro de TVA = UID + MWST, TVA ou IVA](https://www.estv.admin.ch/de/unternehmens-identifikationsnummer-uid) — référence fiable
- [HMRC (gov.uk), COM40011 : préfixe de 2 lettres + jusqu'à 6 caractères, ou jusqu'à 8 chiffres](https://www.gov.uk/hmrc-internal-manuals/cotax-manual/com40011) — référence fiable
- [CRO (opendata.cro.ie), dictionnaire de données : numéro de société numérique](https://opendata.cro.ie/dataset/companies/resource/3fef41bc-b8f4-4b10-8434-ce51c29b1bba) — référence fiable

Source écartée : l'annexe 9 de Skatteverket (VAT des États membres), obsolète (15 pays, ancien format belge à 9 chiffres).
