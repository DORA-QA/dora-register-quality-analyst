# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 3: contractual arrangements (REL-008 to 011, BUS-006 to 011, DQ-005 to 010).

For each check (brief §17.1): compliant case, non-compliant case, limit case, absent table,
empty value, documented exception, location of the occurrences, origin and status.
"""

import pytest

from contracts.check_report import load_registry
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import load_catalog
from rules.business.arrangements import arrangement_rules
from rules.engine import RulesEngine
from tests.test_technical_rules import frame

EF, FE2, P = "529900P784EKW7VFMQ21", "529900WFW9ZXG409UL36", "529900KIWVWB8P3VEK25"
REFERENCE = "2026-12-31"
X1, X2, X3 = "eba_CO:x1", "eba_CO:x2", "eba_CO:x3"


def general(code, kind=X1, overarching=""):
    return {"c0010": code, "c0020": kind, "c0030": overarching, "c0040": "eba_CU:EUR", "c0050": "0"}


def specific(
    code, entity=EF, start="2025-01-01", end="9999-12-31", reason="", notice="30", law="eba_GA:FR"
):
    return {
        "c0010": code,
        "c0020": entity,
        "c0030": P,
        "c0070": start,
        "c0080": end,
        "c0090": reason,
        "c0100": notice,
        "c0110": notice,
        "c0120": law,
    }


def complete(*codes, entity=EF):
    """Every table needed for the contracts to be fully linked."""
    return {
        "B_03.01": [{"c0010": c, "c0020": entity} for c in codes],
        "B_03.02": [{"c0010": c, "c0020": P} for c in codes],
        "B_04.01": [{"c0010": c, "c0020": entity} for c in codes],
    }


def run(b0201, b0202, reference=REFERENCE, **others):
    found = {
        "B_01.01": frame("B_01.01", {"c0010": EF, "c0060": reference}),
        "B_02.01": frame("B_02.01", *b0201),
        "B_02.02": frame("B_02.02", *b0202),
    }
    for table, table_rows in others.items():
        found[table] = frame(table, *table_rows)
    return (
        RulesEngine(arrangement_rules()).run(RoIDataset("ZIP", PackageMetadata(), found)).messages
    )


def codes(*args, **kwargs):
    return sorted(m.code for m in run(*args, **kwargs))


def finding(code, *args, **kwargs):
    return next(m for m in run(*args, **kwargs) if m.code == code)


# ------------------------------------------------------------------ compliant and absent
def test_a_complete_arrangement_raises_nothing():
    assert codes([general("C1")], [specific("C1")], **complete("C1")) == []


def test_absent_tables_raise_nothing():
    assert (
        RulesEngine(arrangement_rules()).run(RoIDataset("ZIP", PackageMetadata(), {})).messages
        == []
    )


# ------------------------------------------------------------------ REL-008 to REL-011, DQ-005
def test_rel_008_entity_of_b_02_02_missing_from_b_04_01():
    tables = complete("C1")
    found = finding(
        "REL-008", [general("C1")], [specific("C1"), specific("C1", entity=FE2)], **tables
    )
    (place,) = found.occurrences
    assert (place.table, place.row, place.column, place.value) == ("B_02.02", 2, "c0020", FE2)
    assert (place.target_table, place.target_column, place.side) == ("B_04.01", "c0020", "source")


def test_rel_008_shared_contract_one_row_per_entity_is_fine():
    tables = complete("C1")
    tables["B_04.01"].append({"c0010": "C1", "c0020": FE2})
    assert codes([general("C1")], [specific("C1"), specific("C1", entity=FE2)], **tables) == []


@pytest.mark.parametrize(("table", "code"), [("B_03.01", "REL-009"), ("B_04.01", "REL-011")])
def test_rel_009_and_011_relation_missing(table, code):
    tables = complete("C1", "C2")
    tables[table] = [r for r in tables[table] if r["c0010"] != "C2"]
    found = codes([general("C1"), general("C2")], [specific("C1"), specific("C2")], **tables)
    assert code in found


def test_rel_010_and_dq_005_are_distinct():
    """P7: an arrangement without B_02.02 (REL-010) is not necessarily unused (DQ-005)."""
    without_detail = codes([general("C1"), general("C2")], [specific("C1")], **complete("C1", "C2"))
    assert "REL-010" in without_detail and "DQ-005" not in without_detail
    unused = codes([general("C1"), general("C2")], [specific("C1")], **complete("C1"))
    assert {"REL-010", "DQ-005"} <= set(unused)


def test_relations_of_an_absent_table_are_not_checked():
    assert codes([general("C1")], [specific("C1")]) == []


# ------------------------------------------------------------------ DQ-006, DQ-007, DQ-008
def test_dq_006_ended_only_when_every_row_ended():
    tables = complete("C1", "C2")
    ended = [specific("C1", end="2025-12-31", reason="eba_CO:x4")]
    partly = [
        specific("C2", end="2025-12-31", reason="eba_CO:x4"),
        specific("C2", entity=EF, start="2024-01-01"),
    ]
    found = finding("DQ-006", [general("C1"), general("C2")], ended + partly, **tables)
    assert [o.value for o in found.occurrences] == ["2025-12-31"] and found.params[
        "reference"
    ] == REFERENCE


def test_dq_007_overarching_without_subsequent():
    tables = complete("CADRE", "SUB", "SEUL")
    b0201 = [general("CADRE", X2), general("SUB", X3, "CADRE"), general("SEUL", X2)]
    b0202 = [specific("CADRE"), specific("SUB"), specific("SEUL")]
    found = finding("DQ-007", b0201, b0202, **tables)
    assert [o.value for o in found.occurrences] == ["SEUL"]


def test_dq_008_future_arrangement():
    assert "DQ-008" in codes(
        [general("C1")], [specific("C1", start="2027-03-01")], **complete("C1")
    )


def test_time_checks_need_a_reference_date():
    found = codes(
        [general("C1")], [specific("C1", end="2020-01-01")], reference="", **complete("C1")
    )
    assert "DQ-006" not in found and "BUS-009" not in found


# ------------------------------------------------------------------ BUS-006, BUS-007
def test_bus_006_reference_on_a_standalone_or_overarching_arrangement():
    b0201 = [general("CADRE", X2), general("C1", X1, "CADRE"), general("SUB", X3, "CADRE")]
    found = finding(
        "BUS-006",
        b0201,
        [specific(c) for c in ("CADRE", "C1", "SUB")],
        **complete("CADRE", "C1", "SUB"),
    )
    assert [(o.row, o.column) for o in found.occurrences] == [(2, "c0030")]


def test_bus_007_subsequent_with_another_provider():
    tables = complete("CADRE", "SUB")
    tables["B_03.02"] = [{"c0010": "CADRE", "c0020": P}, {"c0010": "SUB", "c0020": "AUTRE"}]
    b0201 = [general("CADRE", X2), general("SUB", X3, "CADRE")]
    found = finding("BUS-007", b0201, [specific("CADRE"), specific("SUB")], **tables)
    assert [o.side for o in found.occurrences] == ["source", "target"]


# ------------------------------------------------------------------ BUS-008 to 011, DQ-009, 010


# ------------------------------------------------------------------ BUS-008 to 011, DQ-009, 010
@pytest.mark.parametrize(
    ("row", "code"),
    [
        (specific("C1", start="2026-06-01", end="2026-01-01", reason="eba_CO:x4"), "BUS-008"),
        (specific("C1", end="2025-12-31"), "BUS-009"),
        (specific("C1", reason="eba_CO:x4"), "BUS-010"),
        (specific("C1", start="2026-01-01", end="2026-12-31", notice="400"), "DQ-009"),
        (specific("C1", start="1900-01-01"), "DQ-010"),
        (specific("C1", end="2200-01-01"), "DQ-010"),
    ],
)
def test_dates_of_an_arrangement(row, code):
    assert code in codes([general("C1")], [row], **complete("C1"))


def test_open_end_and_ended_with_reason_are_fine():
    rows = [specific("C1"), specific("C2", end="2025-12-31", reason="eba_CO:x4")]
    found = codes([general("C1"), general("C2")], rows, **complete("C1", "C2"))
    assert found == ["DQ-006"]


@pytest.mark.parametrize("notice", ["1e309", "nan", "inf", "-1e400", "abc"])
def test_a_notice_period_that_is_not_a_number_is_ignored(notice):
    """Fuzzing, 29/10: '1e309' read as infinity used to stop the rule (ENG-001)."""
    row = specific("C1", start="2026-01-01", end="2026-12-31", notice=notice)
    assert codes([general("C1")], [row], **complete("C1")) == []


def test_invalid_dates_are_left_to_the_format_rules():
    assert (
        codes([general("C1")], [specific("C1", start="2026-13-45", end="hier")], **complete("C1"))
        == []
    )


def test_bus_011_governing_law_differs_within_an_arrangement():
    rows = [specific("C1"), specific("C1", entity=FE2, law="eba_GA:DE")]
    tables = complete("C1")
    tables["B_04.01"].append({"c0010": "C1", "c0020": FE2})
    found = finding("BUS-011", [general("C1")], rows, **tables)
    assert sorted(o.value for o in found.occurrences) == ["eba_GA:DE", "eba_GA:FR"]


# ------------------------------------------------------------------ origin and status
EXPECTED = {
    "REL-008": ("MAJOR", "OFFICIAL", "CONFIRMED"),
    "REL-009": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-010": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-011": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-005": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-006": ("INFO", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-007": ("INFO", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-008": ("INFO", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-006": ("MINOR", "OFFICIAL", "CONFIRMED"),
    "BUS-007": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-008": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-009": ("MAJOR", "OFFICIAL", "CONFIRMED"),
    "BUS-010": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-009": ("INFO", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-010": ("INFO", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-011": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
}


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_severity_origin_and_status_follow_the_decisions(code):
    registry = {e["code"]: e for e in load_registry()}
    severity, origin, status = EXPECTED[code]
    assert load_catalog()[code]["severity"] == severity
    assert (registry[code]["origin"], registry[code]["severity_status"]) == (origin, status)
