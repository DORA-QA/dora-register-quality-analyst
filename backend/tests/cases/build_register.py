# SPDX-License-Identifier: EUPL-1.2
# ruff: noqa: E501
"""Génère le registre des cas de test : un cas par erreur, tous dérivés du package golden.

Usage : python -m tests.cases.build_register
Sorties : tests/cases/register.csv (versionné). Le tableur de suivi est produit à partir de lui.
Le Product Owner ne fournit qu'UN fichier : tests/golden/golden.zip (conforme, anonymisé).
"""

import csv
import json
import re
from pathlib import Path

from tests.cases.mutations import MANUAL, MUTATIONS

ROOT = Path(__file__).resolve().parents[3]
REGISTER = Path(__file__).with_name("register.csv")
FAMILIES = {
    "FILE": "Fichier",
    "XML": "XML",
    "ENV": "Enveloppe",
    "ZIP": "Archive",
    "PKG": "Package",
    "CSV": "CSV",
    "IMP": "Import",
    "DAT": "Données",
    "ENG": "Moteur",
    "REL": "Cohérence entre tableaux",
    "BUS": "Règles métier",
    "DQ": "Qualité des données",
    "GLF": "Référentiel GLEIF",
}
FIELDS = [
    "cas",
    "code",
    "famille",
    "erreur_introduite",
    "couverture",
    "severite",
    "statut_severite",
    "valide_sur_donnees_reelles",
    "commentaire",
]


def build_rows() -> list[dict[str, str]]:
    base = ROOT / "backend" / "reference" / "messages"
    catalog = json.loads((base / "catalog.json").read_text("utf-8"))
    french = json.loads((base / "fr.json").read_text("utf-8"))["messages"]
    previous: dict[str, dict[str, str]] = {}
    if REGISTER.exists():
        with REGISTER.open(encoding="utf-8", newline="") as handle:
            previous = {row["cas"]: row for row in csv.DictReader(handle)}
    by_code: dict[str, list] = {}
    for mutation in MUTATIONS:
        by_code.setdefault(mutation.code, []).append(mutation)

    rows = []
    for code in sorted(catalog, key=lambda c: (c.split("-")[0], int(c.split("-")[1]))):
        entries = by_code.get(code) or [None]
        for mutation in entries:
            case = mutation.case if mutation else f"M-{code}"
            description = (
                mutation.description
                if mutation
                else MANUAL.get(code, re.sub(r"\s+", " ", french[code]["message"]))
            )
            old = previous.get(case, {})
            rows.append(
                {
                    "cas": case,
                    "code": code,
                    "famille": FAMILIES.get(code.split("-")[0], ""),
                    "erreur_introduite": description,
                    "couverture": "mutation automatique" if mutation else "à fabriquer",
                    "severite": catalog[code]["severity"],
                    "statut_severite": catalog[code].get("severity_status", "CONFIRMED"),
                    "valide_sur_donnees_reelles": old.get("valide_sur_donnees_reelles", ""),
                    "commentaire": old.get("commentaire", ""),
                }
            )
    return rows


def main() -> None:
    rows = build_rows()
    with REGISTER.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} cas écrits dans {REGISTER}")


if __name__ == "__main__":
    main()
