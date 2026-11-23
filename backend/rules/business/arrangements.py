# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 3: contractual arrangements (brief §7, §9.3; decision P7).

Relations of an arrangement of B_02.01 (brief §7.2)
REL-008  a (contract, entity) pair of B_02.02 is missing from B_04.01 (ITS, B_02.02.0020)
REL-009  arrangement without signing entity in B_03.01
REL-010  arrangement without any row in B_02.02 (missing relation)
REL-011  arrangement without entity making use of it in B_04.01

Use of an arrangement (brief §7.3, decision P7: distinct from REL-010)
DQ-005   arrangement cited nowhere but in B_02.01 (MAJOR)
DQ-006   arrangement ended before the reference date (INFO)
DQ-007   overarching arrangement (x2) cited by no subsequent arrangement (INFO)
DQ-008   arrangement starting after the reference date (INFO)

Overarching and subsequent arrangements (brief §7.4)
BUS-006  B_02.01.0030 filled for a standalone (x1) or overarching (x2) arrangement (ITS)
BUS-007  provider of a subsequent arrangement different from the one of its overarching one

Dates (brief §7.5) and applicable law (brief §9.3)
BUS-008  start date after the end date
BUS-009  arrangement ended without reason of termination (ITS, B_02.02.0090)
BUS-010  reason of termination for an arrangement still running
DQ-009   notice period longer than the arrangement (INFO)
DQ-010   improbable duration: start before 1950, or end between 2100 and 9999-12-30 (INFO)
BUS-011  different governing laws on the rows of one arrangement

Dates are compared only when they are valid ISO 8601 dates (the format has its own rules).
The reference date is B_01.01.0060; without it, the checks on time are not run.
"""

import math
import re
from datetime import date

from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from rules.business.common import ROW_COLUMN, by_code, rows
from rules.technical.locations import describe

STANDALONE, OVERARCHING, SUBSEQUENT = "eba_CO:x1", "eba_CO:x2", "eba_CO:x3"
OPEN_END = "9999-12-31"
EARLIEST_START = "1950-01-01"
LATEST_END = "2100-01-01"
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Tables citing an arrangement (B_02.01.0010) besides B_02.01 itself.
CITING = (
    ("B_02.02", "c0010"),
    ("B_02.03", "c0010"),
    ("B_02.03", "c0020"),
    ("B_03.01", "c0010"),
    ("B_03.02", "c0010"),
    ("B_03.03", "c0010"),
    ("B_04.01", "c0010"),
    ("B_05.02", "c0010"),
    ("B_07.01", "c0010"),
)


def _date(value: str | None) -> date | None:
    if not value or not _ISO.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _finding(code: str, table: str, places: list[Occurrence], lines: list[str], **params):
    message = make_message(code, details=describe(lines), table=table, count=len(lines), **params)
    return with_occurrences(message, places)


def _place(table: str, row: dict, column: str, **target) -> Occurrence:
    return Occurrence(
        table=table, row=row[ROW_COLUMN], column=column, value=row.get(column), **target
    )


def reference_date(dataset: RoIDataset) -> str | None:
    """B_01.01.0060, when it is a valid date."""
    for row in rows(dataset, "B_01.01", "c0060"):
        if _date(row["c0060"]):
            return row["c0060"]
    return None


class _Arrangements:
    """Rows of B_02.01 and B_02.02, read once per rule."""

    def __init__(self, dataset: RoIDataset) -> None:
        self.general = by_code(dataset, "B_02.01", "c0010", "c0020", "c0030")
        self.specific = list(
            rows(
                dataset,
                "B_02.02",
                "c0010",
                "c0020",
                "c0030",
                "c0070",
                "c0080",
                "c0090",
                "c0100",
                "c0110",
                "c0120",
            )
        )


def _keys(dataset: RoIDataset, table: str, *columns: str) -> set:
    found = set()
    for row in rows(dataset, table, *columns):
        values = tuple(row[c] for c in columns)
        if all(values):
            found.add(values if len(values) > 1 else values[0])
    return found


class ArrangementRelationsRule:
    """REL-008 to REL-011 and DQ-005: what every arrangement of B_02.01 is linked to."""

    id = "REL-008"
    codes = ("DQ-005", "REL-008", "REL-009", "REL-010", "REL-011")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        data = _Arrangements(dataset)
        found: list[ValidationMessage] = []
        if "B_04.01" in dataset.tables:
            users = _keys(dataset, "B_04.01", "c0010", "c0020")
            missing = [
                r
                for r in data.specific
                if r["c0010"] and r["c0020"] and (r["c0010"], r["c0020"]) not in users
            ]
            if missing:
                places = [
                    _place(
                        "B_02.02",
                        r,
                        "c0020",
                        target_table="B_04.01",
                        target_column="c0020",
                        side="source",
                    )
                    for r in missing
                ]
                lines = [f"#{r[ROW_COLUMN]} · {r['c0010']!r} / {r['c0020']!r}" for r in missing]
                found.append(_finding("REL-008", "B_02.02", places, lines))
        if not data.general:
            return found
        relations = (
            ("REL-009", "B_03.01", _keys(dataset, "B_03.01", "c0010")),
            ("REL-010", "B_02.02", {r["c0010"] for r in data.specific if r["c0010"]}),
            ("REL-011", "B_04.01", _keys(dataset, "B_04.01", "c0010")),
        )
        for code, table, present in relations:
            if table not in dataset.tables:
                continue
            missing = [r for key, r in data.general.items() if key not in present]
            if missing:
                found.append(self._missing(code, missing, table))
        cited = {value for table, column in CITING for value in _keys(dataset, table, column)}
        cited |= {r["c0030"] for r in data.general.values() if r["c0030"]}
        unused = [r for key, r in data.general.items() if key not in cited]
        if unused:
            found.append(self._missing("DQ-005", unused, None))
        return found

    @staticmethod
    def _missing(code: str, missing: list[dict], target: str | None) -> ValidationMessage:
        places = [
            _place(
                "B_02.01",
                r,
                "c0010",
                target_table=target,
                target_column="c0010" if target else None,
                side="source" if target else None,
            )
            for r in missing
        ]
        lines = [f"#{r[ROW_COLUMN]} · {r['c0010']!r}" for r in missing]
        return _finding(code, "B_02.01", places, lines, target=target or "")


class ArrangementUseRule:
    """DQ-006, DQ-007, DQ-008: ended, overarching never cited, future (information)."""

    id = "DQ-006"
    codes = ("DQ-006", "DQ-007", "DQ-008")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        data = _Arrangements(dataset)
        found: list[ValidationMessage] = []
        reference = reference_date(dataset)
        if reference:
            ends: dict[str, list[dict]] = {}
            for r in data.specific:
                if r["c0010"] and _date(r["c0080"]) and _date(r["c0070"]):
                    ends.setdefault(r["c0010"], []).append(r)
            ended = [
                lines[0] for lines in ends.values() if all(r["c0080"] < reference for r in lines)
            ]
            future = [
                lines[0] for lines in ends.values() if all(r["c0070"] > reference for r in lines)
            ]
            for code, selected, column in (("DQ-006", ended, "c0080"), ("DQ-008", future, "c0070")):
                if selected:
                    places = [_place("B_02.02", r, column) for r in selected]
                    lines = [f"#{r[ROW_COLUMN]} · {r['c0010']!r} : {r[column]}" for r in selected]
                    found.append(_finding(code, "B_02.02", places, lines, reference=reference))
        cited = {r["c0030"] for r in data.general.values() if r["c0030"]}
        lonely = [
            r for key, r in data.general.items() if r["c0020"] == OVERARCHING and key not in cited
        ]
        if lonely:
            places = [_place("B_02.01", r, "c0010") for r in lonely]
            lines = [f"#{r[ROW_COLUMN]} · {r['c0010']!r}" for r in lonely]
            found.append(_finding("DQ-007", "B_02.01", places, lines))
        return found


class OverarchingArrangementRule:
    """BUS-006, BUS-007: reference to the overarching arrangement (brief §7.4)."""

    id = "BUS-006"
    codes = ("BUS-006", "BUS-007")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        data = _Arrangements(dataset)
        found: list[ValidationMessage] = []
        wrong = [
            r
            for r in data.general.values()
            if r["c0030"] and r["c0020"] in (STANDALONE, OVERARCHING)
        ]
        if wrong:
            places = [_place("B_02.01", r, "c0030") for r in wrong]
            lines = [
                f"#{r[ROW_COLUMN]} · {r['c0010']!r} ({r['c0020']}) → {r['c0030']!r}" for r in wrong
            ]
            found.append(_finding("BUS-006", "B_02.01", places, lines))
        providers: dict[str, set[str]] = {}
        for row in rows(dataset, "B_03.02", "c0010", "c0020"):
            if row["c0010"] and row["c0020"]:
                providers.setdefault(row["c0010"], set()).add(row["c0020"])
        places, lines = [], []
        for row in data.general.values():
            parent = data.general.get(row["c0030"]) if row["c0030"] else None
            if row["c0020"] != SUBSEQUENT or parent is None:
                continue
            own, theirs = providers.get(row["c0010"]), providers.get(parent["c0010"])
            if own and theirs and not own & theirs:
                places += [
                    _place(
                        "B_02.01",
                        row,
                        "c0030",
                        target_table="B_03.02",
                        target_column="c0020",
                        side="source",
                    ),
                    _place("B_02.01", parent, "c0010", side="target"),
                ]
                lines.append(
                    f"#{row[ROW_COLUMN]} · {row['c0010']!r} {sorted(own)} ≠ "
                    f"{parent['c0010']!r} {sorted(theirs)}"
                )
        if lines:
            found.append(_finding("BUS-007", "B_02.01", places, lines))
        return found


class ArrangementDatesRule:
    """BUS-008, BUS-009, BUS-010, DQ-009, DQ-010 and BUS-011 on the rows of B_02.02."""

    id = "BUS-008"
    codes = ("BUS-008", "BUS-009", "BUS-010", "BUS-011", "DQ-009", "DQ-010")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        data = _Arrangements(dataset)
        if not data.specific:
            return []
        reference = reference_date(dataset)
        hits: dict[str, tuple[list[Occurrence], list[str]]] = {}

        def add(code: str, row: dict, column: str, text: str) -> None:
            places, lines = hits.setdefault(code, ([], []))
            places.append(_place("B_02.02", row, column))
            lines.append(f"#{row[ROW_COLUMN]} · {row['c0010']!r} : {text}")

        for r in data.specific:
            start, end = _date(r["c0070"]), _date(r["c0080"])
            if start and end and start > end:
                add("BUS-008", r, "c0070", f"{r['c0070']} > {r['c0080']}")
            if reference and end:
                if r["c0080"] < reference and not r["c0090"]:
                    add("BUS-009", r, "c0090", f"B_02.02.0080 = {r['c0080']}")
                if r["c0080"] >= reference and r["c0090"]:
                    add(
                        "BUS-010",
                        r,
                        "c0090",
                        f"B_02.02.0080 = {r['c0080']}, B_02.02.0090 = {r['c0090']}",
                    )
            if start and end and r["c0080"] != OPEN_END:
                duration = (end - start).days
                for column in ("c0100", "c0110"):
                    notice = _days(r[column])
                    if notice is not None and duration >= 0 and notice > duration:
                        add("DQ-009", r, column, f"B_02.02.{column[1:]} = {notice} > {duration}")
            if start and r["c0070"] < EARLIEST_START:
                add("DQ-010", r, "c0070", r["c0070"])
            if end and LATEST_END <= r["c0080"] < OPEN_END:
                add("DQ-010", r, "c0080", r["c0080"])
        found = [
            _finding(code, "B_02.02", places, lines, reference=reference or "")
            for code, (places, lines) in hits.items()
        ]
        found += self._governing_law(data.specific)
        return found

    @staticmethod
    def _governing_law(specific: list[dict]) -> list[ValidationMessage]:
        laws: dict[str, list[dict]] = {}
        for r in specific:
            if r["c0010"] and r["c0120"]:
                laws.setdefault(r["c0010"], []).append(r)
        places, lines = [], []
        for contract, members in laws.items():
            if len({r["c0120"] for r in members}) > 1:
                places += [_place("B_02.02", r, "c0120") for r in members]
                lines.append(f"{contract!r} : {sorted({r['c0120'] for r in members})}")
        if not lines:
            return []
        return [_finding("BUS-011", "B_02.02", places, lines)]


def _days(value: str | None) -> int | None:
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    # "1e309" reads as infinity and "nan" as not-a-number: neither is a notice period.
    return int(number) if math.isfinite(number) else None


def arrangement_rules() -> list:
    return [
        ArrangementRelationsRule(),
        ArrangementUseRule(),
        OverarchingArrangementRule(),
        ArrangementDatesRule(),
    ]
