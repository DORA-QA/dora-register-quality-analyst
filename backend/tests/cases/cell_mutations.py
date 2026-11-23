# SPDX-License-Identifier: EUPL-1.2
"""Mutations de cellules dérivées du modèle de données (phase 1 de CL-18, plan mutations-donnees).

Familles couvertes (les seules dont le code attendu est déjà confirmé dans le catalogue) :
- identifiants : colonnes LEI (``identifier-fields``) → DAT-006 (longueur), DAT-007 (minuscules),
  DAT-010 (clé de contrôle fausse) ;
- longueur maximale (``max-lengths``) → DAT-022.

Chaque variante modifie UNE cellule de la première ligne de la table, dans le golden.
Une colonne qui n'existe pas dans le golden n'a pas de variante : elle est signalée dans
``missing`` (alerte, décision PO de CL-18).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from contracts import data_model
from tests.cases.golden import load_golden
from tests.cases.mutations import _path, _rows, _write
from tests.cases.zip_layout import with_directories

REFERENCE = Path(__file__).resolve().parents[2] / "reference" / "dora"
LEI_FAMILIES = {
    "LEI-LEN": ("DAT-006", "LEI de 19 caractères", lambda lei: lei[:-1]),
    "LEI-CASE": ("DAT-007", "LEI en minuscules", lambda lei: lei.lower()),
    "LEI-CHECK": ("DAT-010", "LEI à la clé de contrôle fausse", lambda lei: lei[:-2] + "13"),
}
LENGTH_FAMILY = ("DAT-022", "dépassement de la longueur maximale")


@dataclass(frozen=True)
class CellVariant:
    case: str
    code: str
    description: str
    table: str
    column: str
    value: str
    package_name: str
    content: bytes


def _split(code: str) -> tuple[str, str]:
    table, number = code.rsplit(".", 1)
    return table, f"c{number}"


def _mutated(table: str, column: str, value: str, row: int = 0):
    golden = load_golden()
    header, rows = _rows(golden, table)
    index = header.index(column)
    original = rows[row][index]
    rows[row][index] = value
    _write(golden, table, header, rows)
    return golden, original


def _variant(case, code, description, table, column, value, row=0):
    golden, _ = _mutated(table, column, value, row)
    return CellVariant(case, code, description, table, column, value, golden.name, golden.to_zip())


def golden_has(table: str, column: str) -> bool:
    golden = load_golden()
    if _path(table) not in golden.files:
        return False
    header, rows = _rows(golden, table)
    return column in header and bool(rows) and rows[0][header.index(column)] != ""


def generate() -> tuple[list[CellVariant], list[str]]:
    """Retourne (variantes, alertes). Les alertes listent les champs sans ligne dans le golden."""
    variants: list[CellVariant] = []
    missing: list[str] = []
    golden = load_golden()
    original_lei = {}

    lei_columns = json.loads((REFERENCE / "identifier-fields-4.0.json").read_text("utf-8"))[
        "lei_columns"
    ]
    for code in lei_columns:
        table, column = _split(code)
        if not golden_has(table, column):
            missing.append(f"{code} (identifiant LEI)")
            continue
        header, rows = _rows(golden, table)
        lei = rows[0][header.index(column)]
        original_lei[code] = lei
        for family, (expected, description, change) in LEI_FAMILIES.items():
            variants.append(
                _variant(
                    f"C-{family}-{code}",
                    expected,
                    f"{description} ({code})",
                    table,
                    column,
                    change(lei),
                )
            )

    # Source du moteur lui-même : seules ces colonnes sont contrôlées par DAT-022.
    for (table, column), limit in sorted(data_model.max_lengths().items()):
        if not golden_has(table, column):
            missing.append(f"{table}.{column} (longueur maximale {limit})")
            continue
        variants.append(
            _variant(
                f"C-LEN-{table}-{column}",
                LENGTH_FAMILY[0],
                f"{LENGTH_FAMILY[1]} ({table} {column}, {limit + 1} caractères)",
                table,
                column,
                "é" * (limit + 1),
            )
        )
    _framework_variants(variants, missing)
    return variants, missing


def _framework_variants(variants: list[CellVariant], missing: list[str]) -> None:
    """RT.02.01.0030 sur la ligne d'un contrat subséquent (x3), pas sur la première ligne.

    Cellule vidée : règle EBA conditionnelle (DAT-024) ; contrat cité inexistant : clé (DAT-005).
    """
    table, column = "B_02.01", "c0030"
    golden = load_golden()
    if _path(table) not in golden.files:
        missing.append(f"{table}.{column} (accord-cadre cité, table absente)")
        return
    header, rows = _rows(golden, table)
    subsequent = next(
        (
            i
            for i, r in enumerate(rows)
            if r[header.index("c0020")] == "eba_CO:x3" and r[header.index(column)]
        ),
        None,
    )
    if subsequent is None:
        missing.append(f"{table}.{column} (accord-cadre cité, aucun contrat subséquent)")
        return
    for case, code, description, value in (
        ("C-FRAMEWORK-EMPTY", "DAT-024", "accord-cadre vidé sur un contrat subséquent", ""),
        ("C-FRAMEWORK-UNKNOWN", "DAT-005", "accord-cadre cité inexistant", "CONTRAT-INCONNU"),
    ):
        variants.append(
            _variant(
                case, code, f"{description} ({table} {column})", table, column, value, subsequent
            )
        )


def export(target: Path) -> int:
    """Écrit les variantes pour la recette manuelle, au format de ``index.csv``."""
    import csv

    variants, missing = generate()
    target.mkdir(parents=True, exist_ok=True)
    with (target / "index.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cas", "code_attendu", "autres_codes_normaux", "description", "fichier"])
        for variant in variants:
            folder = target / variant.case
            folder.mkdir(exist_ok=True)
            (folder / variant.package_name).write_bytes(with_directories(variant.content))
            writer.writerow(
                [
                    variant.case,
                    variant.code,
                    "",
                    variant.description,
                    f"{variant.case}/{variant.package_name}",
                ]
            )
    (target / "non-couverts.txt").write_text("\n".join(missing) + "\n", encoding="utf-8")
    return len(variants)


if __name__ == "__main__":
    import sys

    print(f"{export(Path(sys.argv[1]))} fichiers écrits dans {sys.argv[1]}")
