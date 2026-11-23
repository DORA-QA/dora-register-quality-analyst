# SPDX-License-Identifier: EUPL-1.2
"""Rebuild backend/reference/dora/rule-status-4.0.json from the official EBA list of rules.

Usage (from backend/, standard library only)::

    python -I tools/build_rule_status.py            # check: rebuild, compare, exit 1 on a gap
    python -I tools/build_rule_status.py --write    # rewrite rule-status-4.0.json

Input: the EBA workbook of validation rules kept in ``reference/dora/sources/`` and described in
``reference/dora/rule-status-4.0.provenance.json`` (URL, date, SHA-256). Only the rules of the
DORA framework are read. For each rule:
- id, table, type (column Source), severity, state (IsActive) and expression come from the EBA;
- ``cells`` lists the columns the expression names (``c0010``, ``c0020-0090``, ``c*``), in order;
- ``in_taxonomy`` says whether the rule is in the XBRL taxonomy (``validation-rules-4.0.json``),
  checked against the EBA column "Implemented in XBRL".

Nothing is downloaded. This replaces the export of the professional tool of the PO
(``CONF-ReglesEBA.xlsx``, issue #127, red team RT-11).
"""

import hashlib
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from tools.build_enumerations import read_workbook  # noqa: E402

REFERENCE = BACKEND / "reference" / "dora"
OUTPUT = REFERENCE / "rule-status-4.0.json"
PROVENANCE = REFERENCE / "rule-status-4.0.provenance.json"
FRAMEWORK = "DORA"
SUFFIX = re.compile(r"_\d+$")
CELL = re.compile(r"\b[cC](?:\d{4}(?:-\d{4})?|\*)")


def load_provenance() -> dict:
    return json.loads(PROVENANCE.read_text(encoding="utf-8"))


def rules_source() -> dict:
    return next(i for i in load_provenance()["inputs"] if i["role"] == "rules")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _squash(text: str) -> str:
    return " ".join(text.split())


def cells_of(expression: str) -> str:
    """Columns named by the expression, after its 'with {…}:' header, in order of appearance."""
    body = expression.split(":", 1)[1] if expression.startswith("with") else expression
    return "; ".join(dict.fromkeys(token.lower() for token in CELL.findall(body)))


def build(workbook: Path) -> tuple[dict, list[str]]:
    """The payload of rule-status-4.0.json and the inconsistencies found in the EBA list."""
    rows = next(iter(read_workbook(workbook).values()))
    header = rows[0]
    column = {name: header.index(name) for name in header if name}

    def cell(row: list[str], name: str) -> str:
        index = column[name]
        return row[index] if index < len(row) else ""

    taxonomy = json.loads((REFERENCE / "validation-rules-4.0.json").read_text("utf-8"))["rules"]
    in_taxonomy = {SUFFIX.sub("", rule["id"]) for rule in taxonomy}
    source = rules_source()
    rules, problems = [], []
    for row in rows[1:]:
        if cell(row, "Frameworks") != FRAMEWORK:
            continue
        rule_id = cell(row, "VR Code")
        expression = _squash(cell(row, "Expression"))
        implemented = cell(row, "Implemented in XBRL") == "Yes"
        if implemented != (rule_id in in_taxonomy):
            problems.append(f"{rule_id}: 'Implemented in XBRL' disagrees with the taxonomy")
        rules.append(
            {
                "id": rule_id,
                "table": cell(row, "Tables"),
                "cells": cells_of(expression),
                "type": cell(row, "Source"),
                "severity": cell(row, "Severity"),
                "active": cell(row, "IsActive") == "Active",
                "in_taxonomy": rule_id in in_taxonomy,
                "expression": expression,
            }
        )
    rules.sort(key=lambda rule: rule["id"])
    payload = {
        "source": f"EBA, list of validation rules {source['list']}, framework DORA",
        "list": source["list"],
        "list_date": source["list_date"],
        "rules": rules,
    }
    return payload, problems


def main(arguments: list[str]) -> int:
    source = rules_source()
    path = REFERENCE / source["local_copy"]
    found = sha256(path)
    if found != source["sha256"]:
        print(f"SHA-256 differs: {found} != {source['sha256']} ({path.name})")
        return 1
    payload, problems = build(path)
    for problem in problems:
        print(problem)
    text = json.dumps(payload, indent=1, ensure_ascii=False) + "\n"
    rules = payload["rules"]
    active = sum(rule["active"] for rule in rules)
    if "--write" in arguments:
        OUTPUT.write_text(text, encoding="utf-8")
        print(f"{OUTPUT.name}: {len(rules)} rules, {active} active, written")
        return 1 if problems else 0
    same = OUTPUT.read_text(encoding="utf-8") == text
    print(
        f"{path.name}: SHA-256 ok, {len(rules)} rules, {active} active, "
        f"rule-status-4.0.json {'up to date' if same else 'DIFFERS'}"
    )
    return 0 if same and not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
