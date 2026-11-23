# SPDX-License-Identifier: EUPL-1.2
# ruff: noqa: E501
"""Rebuild backend/reference/dora/max-lengths-4.0.json from the EBA data model (PDF).

Usage (needs the ``pdftotext`` command of poppler-utils, NOT a runtime dependency)::

    python -I tools/build_max_lengths.py "Data_Model_for_DORA_RoI.pdf" OUT.json

Input: the EBA "Data Model for DORA RoI" (version of 1 April 2025, kept in docs/sources).
Pages 2 to 4 hold the detailed table "Table | Column | Type | Length | PrimaryKey | ForeignKey |
Nullable", read in reading order: the column numbers restart at 0010 for each table, in the
order of TABLE_ORDER. Page 1 (the diagram) is read too, only to record where it disagrees with
the detailed table (``diagram_length``). Nothing is downloaded.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

TABLE_ORDER = (
    "B_01.01", "B_01.02", "B_01.03", "B_02.01", "B_02.02", "B_02.03", "B_03.01",
    "B_03.02", "B_03.03", "B_04.01", "B_05.01", "B_05.02", "B_06.01", "B_07.01",
)  # fmt: skip
TYPES = "char|varchar|nvarchar|money|date|int|bit|decimal|binary"
DETAIL = re.compile(
    rf"(\d{{4}}) - (.+?) (?:({TYPES}) )?(\d+) (Yes|No) (Yes|No)(?: (Yes|No))?(?= \d{{4}} - | Yes| No|$)"
)
DIAGRAM = re.compile(r"(\d{4}) - ((?:(?!\d{4} - )[^()])+?) (char|varchar|nvarchar)\((\d+)\)")


def main(pdf: Path, out: Path) -> None:
    text = subprocess.run(
        ["pdftotext", "-raw", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    start = text.index("Table Column Type Length")
    body = re.sub(r"B\.\d\d\.\d\d — [^\n]*\n", "\n", text[start:]).replace("EBA Regular Use#", "")
    body = " ".join(body.split())

    tables: list[list[tuple]] = []
    previous = 10**6
    for match in DETAIL.finditer(body):
        number = int(match.group(1))
        if number <= previous:
            tables.append([])
        tables[-1].append(match.groups())
        previous = number
    if len(tables) != len(TABLE_ORDER):
        raise SystemExit(f"expected {len(TABLE_ORDER)} tables, found {len(tables)}")

    columns = {}
    for table, rows in zip(TABLE_ORDER, tables, strict=True):
        for number, label, kind, length, *_ in rows:
            columns[f"{table}.{number}"] = {
                "code": f"{table}.{number}",
                "label": label.strip(),
                "type": kind or "binary",
                "length": int(length),
            }

    # Diagram (page 1): note the lengths that differ from the detailed table, same label only.
    diagram = " ".join(text[:start].split())
    for number, label, _kind, length in DIAGRAM.findall(diagram):
        for column in columns.values():
            same = column["code"].endswith(number) and column["label"].lower().startswith(
                label.strip().lower()[:30]
            )
            text_column = column["type"] in ("char", "varchar", "nvarchar")
            if same and text_column and int(length) != column["length"]:
                column["diagram_length"] = int(length)

    payload = {
        "source": "EBA, Data Model for DORA RoI (version du 01/04/2025), tableau détaillé des pages 2 à 4",
        "rule": "Longueur maximale en caractères Unicode pour les colonnes char, varchar et nvarchar ; "
        "en cas de désaccord avec le schéma de la page 1 (diagram_length), le tableau détaillé fait foi.",
        "columns": sorted(columns.values(), key=lambda column: column["code"]),
    }
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"{len(columns)} columns, {sum('diagram_length' in c for c in columns.values())} diagram differences"
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
