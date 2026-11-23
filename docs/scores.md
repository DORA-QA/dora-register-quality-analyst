# Scores et profils

Version 0.8.2 · Sprint 4, lots 1 et 2 · décisions du PO du 02/11/2026 (A1, A2, A4) et PO-10 (#13)

> Indicateurs internes de qualité, sans valeur réglementaire. Ils ne préjugent pas de l'acceptation du registre par une autorité compétente.

La formule n'existe qu'à un seul endroit : le module `backend/scoring`. L'interface affiche ce que renvoie l'API et ne recalcule rien.

## 1. Profils

Tous les contrôles s'exécutent toujours. Le profil est une manière de lire les constats, déduite de l'**origine** de chaque code (`backend/reference/checks/checks.json`) :

| Profil | Origines | Sens |
|---|---|---|
| Réglementaire (`REGULATORY`) | `OFFICIAL`, `TECHNICAL` | Textes et règles officiels ; contraintes qui rendent une remise impossible à traiter (A1) |
| Expert (`EXPERT`) | `PO_VALIDATED`, `DATA_QUALITY` | Conseils plus exigeants que les règles officielles. Un constat expert n'est jamais une non-conformité réglementaire |

Un contrôle peut regrouper des codes des deux profils (par exemple DAT-019, réglementaire, et DAT-020, expert) : ses constats se lisent alors code par code. L'API donne `profile` pour chaque constat et `profiles` pour chaque contrôle.

Le champ `edition` du registre (`core`, `expert`) est un autre axe, réservé à une future séparation commerciale du produit (A2) : aucun profil ni aucun score ne le lit.

## 2. Formule (inchangée depuis PO-10)

1. Chaque contrôle pèse le poids de son code le plus grave : BLOCKER 5, MAJOR 3, MINOR 1, INFO 1. Exception : un contrôle marqué `scored: false` dans le registre des contrôles pèse 0 ; il est affiché mais sans effet sur les scores (contrôle des montants, décision du PO dans PO-35).
2. Un contrôle réussi rapporte tout son poids, un contrôle en avertissement la moitié, un contrôle en échec (au moins un BLOCKER) rien.
3. Un contrôle qui concerne le fichier mais n'a pas tourné, ou qui n'a pas pu lire une colonne (« non évalué », RT-09), ne rapporte rien et reste compté dans le total : un fichier qui s'arrête tôt ne peut pas paraître bon.
4. Un contrôle qui ne concerne pas le fichier (contrôle d'enveloppe sur un ZIP) sort du total.
5. Score = poids obtenu / poids total, de 0 à 100, arrondi.

## 3. Les trois indicateurs (A4)

| Indicateur | Périmètre | Valeur |
|---|---|---|
| Score réglementaire | Codes `OFFICIAL` et `TECHNICAL` seulement : chaque contrôle ne garde que ces codes, son poids et son statut sont recalculés sur eux ; un contrôle sans aucun de ces codes est écarté | 0 à 100 |
| Score qualité | Tous les codes (« conformité experte » du PO, 18/10/2026) | 0 à 100 |
| Confiance | Tous les contrôles | 0 dès qu'un contrôle échoue sur un BLOCKER ; 100 si tous les contrôles concernant le fichier ont tourné sans BLOCKER ; « non évaluée » sinon (variante retenue en PO-10) |

Il n'y a pas de score global distinct : le score qualité en tient lieu (brief, §9).

**Règles provisoires** : elles comptent à leur sévérité. L'API indique combien de codes provisoires entrent dans le périmètre (`provisional_codes`) et combien de constats en viennent (`provisional_findings`), pour que l'écran puisse le dire.

**Absence de calcul** (brief, §13) : quand aucun contrôle concernant le fichier n'a tourné, le score vaut `null` et l'état `NOT_EVALUATED`, jamais 0. Un fichier qui n'est pas un registre a bien un score, très bas, parce que la détection a tourné et échoué.

## 4. Ce que renvoie l'API

`POST /api/import` renvoie, en plus des champs de la 0.8.0 (`summary` est inchangé) :

```text
scores.regulatory, scores.quality
  scope            REGULATORY ou QUALITY
  value, state     0 à 100 ou null ; EVALUATED ou NOT_EVALUATED
  weight_earned, weight_total, checks_performed, passed, warnings, failed
  not_run          contrôles concernant le fichier qui n'ont pas tourné
  not_evaluated    contrôles qui n'ont pas pu lire une colonne
  not_applicable   contrôles hors sujet pour ce fichier (hors total)
  origins, categories, severities   familles prises en compte
  provisional_codes, provisional_findings
scores.confidence  value (100, 0 ou null), state, not_run
scores.computed_at, scores.engine_version
engine             version, catalog_codes, catalog_fingerprint (SHA-256 du registre et du catalogue, 12 caractères), taxonomy_version
messages[].profile, checks[].profiles
concentration_state   EVALUATED, NOT_APPLICABLE (pas de ligne B_02.02) ou INSUFFICIENT_DATA (calcul impossible)
```

## 5. Tests

`backend/tests/test_scoring.py` (profils, restriction, formule, confiance) et `backend/tests/test_api_scores.py` (contrat de l'API). Le score qualité est vérifié égal à la formule de la 0.8.0 appliquée à tous les contrôles.
