# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 4: functions and assessment of the ICT services (brief §8, §7.5, 29/10).

Identifier of a function (brief §8.1)
BUS-012  identifier not in the form 'F' + natural number (ITS, B_06.01.0010)
BUS-013  same identifier used for several entities (ITS: one identifier per combination)

Coverage (brief §8.2)
REL-012  critical or important function without any row in B_02.02 (BLOCKER, provisional)
DQ-011   other function without any row in B_02.02 (INFO)

Assessment (brief §8.3, §8.4)
BUS-015  assessment inconsistent: not assessed but dated, critical with RTO or RPO at 0,
         critical with an impact not assessed
BUS-016  critical function without reasons of criticality (advice)
DQ-012   same function name assessed critical for one entity and not for another
DQ-013   non-critical function looking critical: RTO of 4 hours or less, or high impact (INFO)
BUS-017  date of assessment (B_06.01.0070) or of audit (B_07.01.0070) after the reference date

Services supporting a critical function (brief §8.4; addition of 29/10)
REL-013  service of a critical function missing from B_07.01 (ITS, B_07.01)
REL-014  row of B_07.01 matching no row of B_02.02 (contract, provider, type of service)
REL-015  level of reliance (B_02.02.0180) reported for a non-critical function (advice)
REL-016  level of reliance empty for a critical function (ITS, B_02.02.0180)
REL-017  no exit plan (B_07.01.0080 = No) for a service supporting a critical function (advice)
"""

import re

from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from rules.business.arrangements import _date, reference_date
from rules.business.common import ROW_COLUMN, normalise_name, rows
from rules.technical.locations import describe

YES, NO, NOT_ASSESSED = "eba_BT:x28", "eba_BT:x29", "eba_BT:x21"
HIGH_IMPACT, IMPACT_NOT_ASSESSED = "eba_ZZ:x793", "eba_ZZ:x799"
OPEN_DATE = "9999-12-31"
SHORT_RTO_HOURS = 4
_FUNCTION_ID = re.compile(r"^F[1-9]\d*$")


def _finding(code: str, table: str, places: list[Occurrence], lines: list[str], **params):
    message = make_message(code, details=describe(lines), table=table, count=len(lines), **params)
    return with_occurrences(message, places)


# Where the criticality of the function is read (#168: the target in every occurrence).
CRITICALITY = {"target_table": "B_06.01", "target_column": "c0050", "side": "source"}


def _place(table: str, row: dict, column: str, **target) -> Occurrence:
    return Occurrence(
        table=table, row=row[ROW_COLUMN], column=column, value=row.get(column), **target
    )


def _hours(value: str | None) -> float | None:
    try:
        number = float(value) if value else None
    except ValueError:
        return None
    return (
        number if number is not None and number == number and abs(number) != float("inf") else None
    )


class _Functions:
    """B_06.01, B_02.02 and B_07.01 as the rules of this lot need them."""

    def __init__(self, dataset: RoIDataset) -> None:
        self.functions = list(
            rows(
                dataset,
                "B_06.01",
                "c0010",
                "c0020",
                "c0030",
                "c0040",
                "c0050",
                "c0060",
                "c0070",
                "c0080",
                "c0090",
                "c0100",
            )
        )
        self.criticality = {
            (f["c0010"], f["c0040"]): f["c0050"]
            for f in self.functions
            if f["c0010"] and f["c0040"]
        }
        self.services = list(
            rows(dataset, "B_02.02", "c0010", "c0020", "c0030", "c0050", "c0060", "c0180")
        )
        self.assessments = list(
            rows(dataset, "B_07.01", "c0010", "c0020", "c0040", "c0070", "c0080")
        )
        self.has_services = "B_02.02" in dataset.tables
        self.has_assessments = "B_07.01" in dataset.tables

    def is_critical(self, service: dict) -> bool | None:
        """True or False for a known function of the same entity; None otherwise (DAT-005, R7)."""
        value = self.criticality.get((service["c0050"], service["c0020"]))
        return None if value is None else value == YES


class FunctionIdentifierRule:
    """BUS-012, BUS-013: format and uniqueness of the function identifier (ITS, B_06.01.0010)."""

    id = "BUS-012"
    codes = ("BUS-012", "BUS-013")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        data = _Functions(dataset)
        found: list[ValidationMessage] = []
        wrong = [f for f in data.functions if f["c0010"] and not _FUNCTION_ID.match(f["c0010"])]
        if wrong:
            places = [_place("B_06.01", f, "c0010") for f in wrong]
            lines = [f"#{f[ROW_COLUMN]} · {f['c0010']!r}" for f in wrong]
            found.append(_finding("BUS-012", "B_06.01", places, lines))
        entities: dict[str, list[dict]] = {}
        for f in data.functions:
            if f["c0010"] and f["c0040"]:
                entities.setdefault(f["c0010"], []).append(f)
        places, lines = [], []
        for identifier, members in entities.items():
            if len({f["c0040"] for f in members}) > 1:
                places += [_place("B_06.01", f, "c0040") for f in members]
                lines.append(f"{identifier!r} : {sorted({f['c0040'] for f in members})}")
        if lines:
            found.append(_finding("BUS-013", "B_06.01", places, lines))
        return found


class FunctionCoverageRule:
    """REL-012 (critical, BLOCKER provisional), DQ-011 (other, INFO): function without B_02.02."""

    id = "REL-012"
    codes = ("DQ-011", "REL-012")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        data = _Functions(dataset)
        if not data.has_services:
            return []
        covered = {(s["c0050"], s["c0020"]) for s in data.services}
        found: list[ValidationMessage] = []
        for code, critical in (("REL-012", True), ("DQ-011", False)):
            missing = [
                f
                for f in data.functions
                if f["c0010"]
                and f["c0040"]
                and (f["c0050"] == YES) is critical
                and (f["c0010"], f["c0040"]) not in covered
            ]
            if missing:
                places = [
                    _place(
                        "B_06.01",
                        f,
                        "c0010",
                        target_table="B_02.02",
                        target_column="c0050",
                        side="source",
                    )
                    for f in missing
                ]
                lines = [f"#{f[ROW_COLUMN]} · {f['c0010']!r} ({f['c0040']})" for f in missing]
                found.append(_finding(code, "B_06.01", places, lines))
        return found


class FunctionAssessmentRule:
    """BUS-015, BUS-016, DQ-012, DQ-013, BUS-017 on the assessment of the functions."""

    id = "BUS-015"
    codes = ("BUS-015", "BUS-016", "BUS-017", "DQ-012", "DQ-013")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        data = _Functions(dataset)
        hits: dict[str, tuple[str, list[Occurrence], list[str]]] = {}

        def add(code: str, table: str, row: dict, column: str, text: str) -> None:
            _, places, lines = hits.setdefault(code, (table, [], []))
            places.append(_place(table, row, column))
            lines.append(f"#{row[ROW_COLUMN]} · {text}")

        reference = reference_date(dataset)
        for f in data.functions:
            name = f"{f['c0010']!r} ({f['c0040']})"
            critical = f["c0050"] == YES
            if f["c0050"] == NOT_ASSESSED and f["c0070"] and f["c0070"] != OPEN_DATE:
                add(
                    "BUS-015",
                    "B_06.01",
                    f,
                    "c0070",
                    f"{name} : B_06.01.0050 = {f['c0050']}, B_06.01.0070 = {f['c0070']}",
                )
            if critical:
                for column in ("c0080", "c0090"):
                    if _hours(f[column]) == 0:
                        add("BUS-015", "B_06.01", f, column, f"{name} : B_06.01.{column[1:]} = 0")
                if f["c0100"] == IMPACT_NOT_ASSESSED:
                    add("BUS-015", "B_06.01", f, "c0100", f"{name} : B_06.01.0100 = {f['c0100']}")
                if not f["c0060"]:
                    add("BUS-016", "B_06.01", f, "c0060", f"{name} : B_06.01.0060 = ''")
            elif f["c0050"] == NO:
                rto = _hours(f["c0080"])
                if (rto is not None and 0 < rto <= SHORT_RTO_HOURS) or f["c0100"] == HIGH_IMPACT:
                    add(
                        "DQ-013",
                        "B_06.01",
                        f,
                        "c0050",
                        f"{name} : B_06.01.0080 = {f['c0080']}, B_06.01.0100 = {f['c0100']}",
                    )
            if (
                reference
                and _date(f["c0070"])
                and f["c0070"] != OPEN_DATE
                and f["c0070"] > reference
            ):
                add("BUS-017", "B_06.01", f, "c0070", f"{name} : B_06.01.0070 = {f['c0070']}")
        for a in data.assessments:
            if (
                reference
                and _date(a["c0070"])
                and a["c0070"] != OPEN_DATE
                and a["c0070"] > reference
            ):
                add(
                    "BUS-017",
                    "B_07.01",
                    a,
                    "c0070",
                    f"{a['c0010']!r} : B_07.01.0070 = {a['c0070']}",
                )
        found = [
            _finding(code, table, places, lines, reference=reference or "")
            for code, (table, places, lines) in hits.items()
        ]
        found += self._divergent_criticality(data.functions)
        return found

    @staticmethod
    def _divergent_criticality(functions: list[dict]) -> list[ValidationMessage]:
        by_name: dict[str, list[dict]] = {}
        for f in functions:
            if f["c0030"] and f["c0050"] in (YES, NO):
                by_name.setdefault(normalise_name(f["c0030"]), []).append(f)
        places, lines = [], []
        for members in by_name.values():
            if len({f["c0050"] for f in members}) > 1:
                places += [_place("B_06.01", f, "c0050") for f in members]
                lines.append(
                    ", ".join(f"#{f[ROW_COLUMN]} {f['c0040']} {f['c0050']}" for f in members)
                )
        if not lines:
            return []
        return [_finding("DQ-012", "B_06.01", places, lines)]


class CriticalServiceRule:
    """REL-013 to REL-017: services of a critical function, B_07.01 and the level of reliance."""

    id = "REL-013"
    codes = ("REL-013", "REL-014", "REL-015", "REL-016", "REL-017")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        data = _Functions(dataset)
        if not data.services:
            return []
        hits: dict[str, tuple[str, list[Occurrence], list[str]]] = {}

        def add(code: str, table: str, place: Occurrence, text: str) -> None:
            _, places, lines = hits.setdefault(code, (table, [], []))
            places.append(place)
            lines.append(text)

        assessed = {(a["c0010"], a["c0020"], a["c0040"]): a for a in data.assessments}
        critical_keys: set[tuple] = set()
        service_keys = {(s["c0010"], s["c0030"], s["c0060"]) for s in data.services}
        for s in data.services:
            critical = data.is_critical(s)
            key = (s["c0010"], s["c0030"], s["c0060"])
            text = f"#{s[ROW_COLUMN]} · {s['c0010']!r} / {s['c0050']} / {s['c0060']}"
            if critical is None:
                continue
            if critical:
                critical_keys.add(key)
                if not s["c0180"]:
                    add("REL-016", "B_02.02", _place("B_02.02", s, "c0180", **CRITICALITY), text)
                if data.has_assessments and all(key) and key not in assessed:
                    add(
                        "REL-013",
                        "B_02.02",
                        _place(
                            "B_02.02",
                            s,
                            "c0060",
                            target_table="B_07.01",
                            target_column="c0040",
                            side="source",
                        ),
                        text,
                    )
            elif s["c0180"]:
                add("REL-015", "B_02.02", _place("B_02.02", s, "c0180", **CRITICALITY), text)
        for a in data.assessments:
            key = (a["c0010"], a["c0020"], a["c0040"])
            text = f"#{a[ROW_COLUMN]} · {a['c0010']!r} / {a['c0020']} / {a['c0040']}"
            if all(key) and key not in service_keys:
                add(
                    "REL-014",
                    "B_07.01",
                    _place(
                        "B_07.01",
                        a,
                        "c0040",
                        target_table="B_02.02",
                        target_column="c0060",
                        side="source",
                    ),
                    text,
                )
            elif key in critical_keys and a["c0080"] == NO:
                add("REL-017", "B_07.01", _place("B_07.01", a, "c0080", **CRITICALITY), text)
        return [
            _finding(code, table, places, lines) for code, (table, places, lines) in hits.items()
        ]


def function_rules() -> list:
    return [
        FunctionIdentifierRule(),
        FunctionCoverageRule(),
        FunctionAssessmentRule(),
        CriticalServiceRule(),
    ]
