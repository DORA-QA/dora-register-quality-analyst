# SPDX-License-Identifier: EUPL-1.2
"""Data model of the DORA register: columns, primary keys and key constraints.

Read from ``reference/dora`` (generated from the EBA taxonomy, see
``tools/build_reference.py``, plus ``key-constraints-4.0.json``). Engines read it
here, so that they depend on ``contracts`` only.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "reference" / "dora"
DEFAULT_VERSION = "4.0"


@dataclass(frozen=True)
class KeyConstraint:
    """Values of ``source_columns`` must exist, together, in ``target_columns``."""

    id: str
    name: str
    source_table: str
    source_columns: tuple[str, ...]
    target_table: str
    target_columns: tuple[str, ...]


@dataclass(frozen=True)
class TableModel:
    code: str
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]


@lru_cache
def tables(version: str = DEFAULT_VERSION) -> dict[str, TableModel]:
    fields = json.loads((REFERENCE_DIR / f"fields-{version}.json").read_text("utf-8"))["fields"]
    columns: dict[str, list[str]] = {}
    keys: dict[str, list[str]] = {}
    for entry in fields:
        columns.setdefault(entry["table"], []).append(entry["csv_column"])
        if entry["primary_key"]:
            keys.setdefault(entry["table"], []).append(entry["csv_column"])
    return {
        code: TableModel(code, tuple(cols), tuple(keys.get(code, ())))
        for code, cols in columns.items()
    }


# Key columns that may be empty, with the condition that makes them mandatory:
# (table, column) -> (column of the same row, value that makes the key column mandatory).
# B_04.01.0040: "Mandatory if the financial entity making use of the ICT service(s) is a
# branch of a financial entity (B_04.01.0030)", Implementing Regulation (EU) 2024/2956, annex.
CONDITIONAL_KEY_COLUMNS = {("B_04.01", "c0040"): ("c0030", "eba_ZZ:x838")}
# Value expected in such a column when it does not apply (EBA Q&A 2024_7282, FAQ 64): free text.
NOT_APPLICABLE = "Not Applicable"


@lru_cache
def mandatory_fields(version: str = DEFAULT_VERSION) -> tuple[tuple[str, str], ...]:
    """(table, column) of the fields the taxonomy declares mandatory (existence rules)."""
    fields = json.loads((REFERENCE_DIR / f"fields-{version}.json").read_text("utf-8"))["fields"]
    return tuple((f["table"], f["csv_column"]) for f in fields if f["mandatory"])


def is_not_applicable(value: str | None) -> bool:
    return value is not None and value.strip().casefold() == NOT_APPLICABLE.casefold()


def optional_key_columns(table: str) -> frozenset[str]:
    return frozenset(c for t, c in CONDITIONAL_KEY_COLUMNS if t == table)


@lru_cache
def key_constraints(version: str = DEFAULT_VERSION) -> tuple[KeyConstraint, ...]:
    raw = json.loads((REFERENCE_DIR / f"key-constraints-{version}.json").read_text("utf-8"))
    return tuple(
        KeyConstraint(
            id=item["id"],
            name=item["name"],
            source_table=item["source_table"],
            source_columns=tuple(item["source_columns"]),
            target_table=item["target_table"],
            target_columns=tuple(item["target_columns"]),
        )
        for item in raw["constraints"]
    )


@dataclass(frozen=True)
class IdentifierFields:
    """Columns that hold a LEI, and columns that hold an identifier typed by another column."""

    # (table, column): always a LEI.
    lei_columns: tuple[tuple[str, str], ...]
    # (table, identifier column, type column): the kind depends on the type column.
    typed: tuple[tuple[str, str, str], ...]
    lei_member: str
    euid_member: str


def _split(reference: str) -> tuple[str, str]:
    table, number = reference.rsplit(".", 1)
    return table, f"c{number}"


@lru_cache
def identifier_fields(version: str = DEFAULT_VERSION) -> IdentifierFields:
    raw = json.loads((REFERENCE_DIR / f"identifier-fields-{version}.json").read_text("utf-8"))
    typed = []
    for item in raw["typed_identifiers"]:
        table, column = _split(item["code"])
        typed.append((table, column, _split(item["type"])[1]))
    return IdentifierFields(
        lei_columns=tuple(_split(code) for code in raw["lei_columns"]),
        typed=tuple(typed),
        lei_member=raw["type_members"]["LEI"],
        euid_member=raw["type_members"]["EUID"],
    )


@lru_cache
def numeric_columns(version: str = DEFAULT_VERSION) -> tuple[tuple[str, str], ...]:
    """(table, column) of every monetary ('m') or integer ('i') column."""
    fields = json.loads((REFERENCE_DIR / f"fields-{version}.json").read_text("utf-8"))["fields"]
    return tuple((f["table"], f["csv_column"]) for f in fields if f["type"] in ("m", "i"))


@dataclass(frozen=True)
class ClosedList:
    """Codes allowed in a field with a closed list (EBA taxonomy, AllowedValue)."""

    id: str
    codes: frozenset[str]
    labels: dict[str, str]


@lru_cache
def closed_lists(version: str = DEFAULT_VERSION) -> dict[tuple[str, str], ClosedList]:
    """(table, column) -> closed list, for the 41 fields of the taxonomy that have one."""
    raw = json.loads((REFERENCE_DIR / f"enumerations-{version}.json").read_text("utf-8"))
    lists = {
        lst["id"]: ClosedList(
            lst["id"],
            frozenset(v["code"] for v in lst["values"]),
            {v["code"]: v["label"] for v in lst["values"]},
        )
        for lst in raw["lists"]
    }
    fields = json.loads((REFERENCE_DIR / f"fields-{version}.json").read_text("utf-8"))["fields"]
    return {
        (f["table"], f["csv_column"]): lists[f["enumeration"]] for f in fields if f["enumeration"]
    }


TEXT_TYPES = ("char", "varchar", "nvarchar")


@lru_cache
def max_lengths(version: str = DEFAULT_VERSION) -> dict[tuple[str, str], int]:
    """(table, column) -> maximum length in characters, for the free-text columns.

    Only columns of the data model typed char/varchar/nvarchar that hold free text in the
    taxonomy ('s'); LEI columns are left to the LEI checks, coded columns to the lists.
    """
    lengths = json.loads((REFERENCE_DIR / f"max-lengths-{version}.json").read_text("utf-8"))
    fields = json.loads((REFERENCE_DIR / f"fields-{version}.json").read_text("utf-8"))["fields"]
    text_columns = {f["code"] for f in fields if f["type"] == "s"}
    lei = set(identifier_fields(version).lei_columns)
    result = {}
    for column in lengths["columns"]:
        place = _split(column["code"])
        if (
            column["type"] in TEXT_TYPES
            and column["length"] > 0
            and column["code"] in text_columns
            and place not in lei
        ):
            result[place] = column["length"]
    return result


@dataclass(frozen=True)
class RuleStatus:
    """An EBA validation rule and whether the EBA list has it switched on."""

    id: str
    table: str
    kind: str
    active: bool
    in_taxonomy: bool
    expression: str
    cells: tuple[str, ...] = ()
    # Severity under which the EBA publishes the rule: "error" or "warning".
    severity: str = "warning"


@lru_cache
def rule_status(version: str = DEFAULT_VERSION) -> dict[str, RuleStatus]:
    """Every rule of the EBA list, by id. Only active rules may produce findings."""
    raw = json.loads((REFERENCE_DIR / f"rule-status-{version}.json").read_text("utf-8"))
    return {
        item["id"]: RuleStatus(
            id=item["id"],
            table=item["table"],
            kind=item["type"],
            active=item["active"],
            in_taxonomy=item["in_taxonomy"],
            expression=item["expression"],
            cells=tuple(c.strip() for c in str(item.get("cells") or "").split(";") if c.strip()),
            severity=str(item.get("severity") or "warning").lower(),
        )
        for item in raw["rules"]
    }


def eba_severity(official_codes: tuple[str, ...], version: str = DEFAULT_VERSION) -> str | None:
    """Severity published by the EBA for the rules behind a finding (``EBA.V8825``).

    "error" if one of them is an error, "warning" if all are warnings, None when the finding
    applies no EBA validation rule (PO, #179: the badge says so next to our own severity).
    """
    by_number = {rule.id.split("_")[0].lower(): rule for rule in rule_status(version).values()}
    found = [
        by_number[code.split(".", 1)[1].lower()].severity
        for code in official_codes
        if code.upper().startswith("EBA.V") and code.split(".", 1)[1].lower() in by_number
    ]
    if not found:
        return None
    return "error" if "error" in found else "warning"


def active_rules(version: str = DEFAULT_VERSION) -> tuple[RuleStatus, ...]:
    return tuple(rule for rule in rule_status(version).values() if rule.active)


@lru_cache
def eea_countries() -> frozenset[str]:
    raw = json.loads((REFERENCE_DIR / "eea-countries.json").read_text("utf-8"))
    return frozenset(raw["countries"])


@lru_cache
def _official_labels(version: str = DEFAULT_VERSION) -> dict[str, dict[str, dict[str, str]]]:
    raw = json.loads((REFERENCE_DIR / f"labels-{version}.json").read_text("utf-8"))
    return {
        "fields": raw.get("fields", {}),
        "members": raw.get("members", {}),
        "tables": raw.get("tables", {}),
    }


@lru_cache
def _eba_labels(version: str = DEFAULT_VERSION) -> tuple[dict[str, str], dict[str, str]]:
    """English labels of the EBA data model, used until the ITS labels are in (#179)."""
    fields = json.loads((REFERENCE_DIR / f"fields-{version}.json").read_text("utf-8"))["fields"]
    lists = json.loads((REFERENCE_DIR / f"enumerations-{version}.json").read_text("utf-8"))
    members = {v["code"]: v["label"] for item in lists["lists"] for v in item["values"]}
    return {f["code"]: f["name"] for f in fields}, members


def label(kind: str, code: str, language: str, version: str = DEFAULT_VERSION) -> str | None:
    """Official label of a field (``B_07.01.0050``), a list member (``eba_ZZ:x959``) or a
    template (``B_07.01``).

    Order (PO, #179): the official ITS 2024/2956 label in the language asked, then in English,
    then the English label of the EBA data model; None when the code is unknown.
    """
    section = {"field": "fields", "member": "members", "table": "tables"}[kind]
    official = _official_labels(version).get(section, {})
    entry = official.get(code) or official.get(code.lower()) or {}
    for candidate in (language, "en"):
        if entry.get(candidate):
            return str(entry[candidate])
    if kind == "table":
        return None
    fields, members = _eba_labels(version)
    if kind == "field":
        return fields.get(code)
    return members.get(code) or next(
        (text for key, text in members.items() if key.lower() == code.lower()), None
    )
