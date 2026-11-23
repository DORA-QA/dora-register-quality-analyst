# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 4: functions (BUS-012, 013, 015 to 017, REL-012 to 017, DQ-011 to 013).

For each check (brief §17.1): compliant case, non-compliant case, limit case, absent table,
empty value, documented exception, location of the occurrences, origin and status.
"""

import pytest

from contracts.check_report import load_registry
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import load_catalog
from rules.business.functions import function_rules
from rules.engine import RulesEngine
from tests.test_technical_rules import frame

EF, FE2, P = "529900P784EKW7VFMQ21", "529900WFW9ZXG409UL36", "529900KIWVWB8P3VEK25"
YES, NO, NOT_ASSESSED = "eba_BT:x28", "eba_BT:x29", "eba_BT:x21"
REFERENCE = "2026-12-31"


def function(code="F1", entity=EF, critical=YES, **cells):
    row = {
        "c0010": code,
        "c0020": "eba_TA:x182",
        "c0030": f"FONCTION {code}",
        "c0040": entity,
        "c0050": critical,
        "c0060": "MOTIF",
        "c0070": "2026-10-01",
        "c0080": "8",
        "c0090": "24",
        "c0100": "eba_ZZ:x792",
    }
    return {**row, **cells}


def service(function_id="F1", entity=EF, contract="C1", kind="eba_TA:S15", reliance="x795"):
    return {
        "c0010": contract,
        "c0020": entity,
        "c0030": P,
        "c0050": function_id,
        "c0060": kind,
        "c0180": f"eba_ZZ:{reliance}" if reliance else "",
    }


def assessment(contract="C1", kind="eba_TA:S15", audit="2026-07-01", exit_plan=YES):
    return {"c0010": contract, "c0020": P, "c0040": kind, "c0070": audit, "c0080": exit_plan}


def run(b0601, b0202=None, b0701=None, reference=REFERENCE):
    found = {
        "B_01.01": frame("B_01.01", {"c0010": EF, "c0060": reference}),
        "B_06.01": frame("B_06.01", *b0601),
    }
    if b0202 is not None:
        found["B_02.02"] = frame("B_02.02", *b0202)
    if b0701 is not None:
        found["B_07.01"] = frame("B_07.01", *b0701)
    return RulesEngine(function_rules()).run(RoIDataset("ZIP", PackageMetadata(), found)).messages


def codes(*args, **kwargs):
    return sorted(m.code for m in run(*args, **kwargs))


def finding(code, *args, **kwargs):
    return next(m for m in run(*args, **kwargs) if m.code == code)


# ------------------------------------------------------------------ compliant and absent
def test_a_complete_critical_function_raises_nothing():
    assert codes([function()], [service()], [assessment()]) == []


def test_absent_tables_raise_nothing():
    messages = RulesEngine(function_rules()).run(RoIDataset("ZIP", PackageMetadata(), {}))
    assert messages.messages == []


def test_without_b_02_02_coverage_is_not_checked():
    assert codes([function(), function("F2", critical=NO)]) == []


# ------------------------------------------------------------------ BUS-012, BUS-013
@pytest.mark.parametrize("identifier", ["FCT-001", "f1", "F0", "F01", "F", "F1A"])
def test_bus_012_identifier_not_in_the_form_f_number(identifier):
    found = finding("BUS-012", [function(identifier)])
    assert [(o.row, o.column, o.value) for o in found.occurrences] == [(1, "c0010", identifier)]


@pytest.mark.parametrize("identifier", ["F1", "F9", "F10", "F123"])
def test_bus_012_valid_identifiers(identifier):
    assert "BUS-012" not in codes([function(identifier)])


def test_bus_013_same_identifier_for_two_entities():
    found = finding("BUS-013", [function(), function(entity=FE2)])
    assert sorted(o.value for o in found.occurrences) == [EF, FE2]


def test_bus_013_two_identifiers_for_one_entity_are_fine():
    assert "BUS-013" not in codes([function("F1"), function("F2")])


# ------------------------------------------------------------------ REL-012, DQ-011
def test_rel_012_critical_function_without_arrangement():
    found = finding("REL-012", [function(), function("F2")], [service()], [assessment()])
    (place,) = found.occurrences
    assert (place.table, place.row, place.value, place.target_table) == (
        "B_06.01",
        2,
        "F2",
        "B_02.02",
    )


def test_rel_012_coverage_is_per_entity():
    """F1 of FE2 is not covered by a B_02.02 row of EF (key: identifier and LEI)."""
    found = codes([function(), function(entity=FE2)], [service()], [assessment()])
    assert "REL-012" in found


def test_dq_011_other_function_without_arrangement():
    found = codes([function(), function("F2", critical=NO)], [service()], [assessment()])
    assert found == ["DQ-011"]


def test_a_function_not_assessed_without_arrangement_is_dq_011():
    found = codes(
        [function(), function("F2", critical=NOT_ASSESSED, c0070="")], [service()], [assessment()]
    )
    assert found == ["DQ-011"]


# ------------------------------------------------------------------ BUS-015, BUS-016
@pytest.mark.parametrize(
    ("cells", "column"),
    [
        ({"c0080": "0"}, "c0080"),
        ({"c0090": "0"}, "c0090"),
        ({"c0090": "0.0"}, "c0090"),
        ({"c0100": "eba_ZZ:x799"}, "c0100"),
    ],
)
def test_bus_015_critical_function_with_undefined_values(cells, column):
    found = finding("BUS-015", [function(**cells)])
    assert [o.column for o in found.occurrences] == [column]


def test_bus_015_function_not_assessed_but_dated():
    found = finding("BUS-015", [function(critical=NOT_ASSESSED, c0070="2026-01-01")])
    assert [(o.column, o.value) for o in found.occurrences] == [("c0070", "2026-01-01")]


def test_bus_015_not_assessed_with_open_date_is_fine():
    assert codes([function(critical=NOT_ASSESSED, c0070="9999-12-31")]) == []


def test_bus_015_non_critical_with_zero_rto_is_fine():
    assert codes([function(critical=NO, c0080="0", c0090="0", c0100="eba_ZZ:x791")]) == []


@pytest.mark.parametrize("value", ["", "abc", "nan", "inf", "1e309"])
def test_bus_015_rto_that_is_not_a_number_is_ignored(value):
    assert "BUS-015" not in codes([function(c0080=value)])


def test_bus_016_critical_function_without_reasons():
    found = finding("BUS-016", [function(c0060=""), function("F2", critical=NO, c0060="")])
    assert [o.row for o in found.occurrences] == [1]


# ------------------------------------------------------------------ BUS-017
def test_bus_017_assessment_and_audit_after_the_reference_date():
    found = finding(
        "BUS-017",
        [function(c0070="2027-01-15")],
        [service()],
        [assessment(audit="2027-02-01")],
    )
    assert [(o.table, o.value) for o in found.occurrences] == [
        ("B_06.01", "2027-01-15"),
        ("B_07.01", "2027-02-01"),
    ]
    assert found.params["reference"] == REFERENCE


@pytest.mark.parametrize("date", ["2026-12-31", "9999-12-31", "2026-13-45", "demain", ""])
def test_bus_017_limit_and_invalid_dates(date):
    assert "BUS-017" not in codes([function(c0070=date)], [service()], [assessment(audit=date)])


def test_bus_017_needs_a_reference_date():
    assert codes([function(c0070="2030-01-01")], reference="") == []


# ------------------------------------------------------------------ DQ-012, DQ-013
def test_dq_012_same_name_critical_for_one_entity_only():
    rows = [
        function(c0030="Paiements"),
        function("F2", entity=FE2, critical=NO, c0030="  PAIEMENTS "),
    ]
    found = finding("DQ-012", rows)
    assert [o.value for o in found.occurrences] == [YES, NO]


def test_dq_012_not_assessed_is_not_compared():
    rows = [function(c0030="X"), function("F2", critical=NOT_ASSESSED, c0030="X", c0070="")]
    assert "DQ-012" not in codes(rows)


@pytest.mark.parametrize(
    ("cells", "expected"),
    [
        ({"c0080": "4"}, True),
        ({"c0080": "0.5"}, True),
        ({"c0080": "5"}, False),
        ({"c0080": "0"}, False),
        ({"c0080": "48", "c0100": "eba_ZZ:x793"}, True),
    ],
)
def test_dq_013_non_critical_function_looking_critical(cells, expected):
    row = function(critical=NO, **{"c0080": "48", "c0100": "eba_ZZ:x791", **cells})
    assert ("DQ-013" in codes([row])) is expected


# ------------------------------------------------------------------ REL-013, REL-014
def test_rel_013_service_of_a_critical_function_missing_from_b_07_01():
    found = finding("REL-013", [function()], [service()], [assessment(kind="eba_TA:S14")])
    (place,) = found.occurrences
    assert (place.table, place.column, place.target_table, place.target_column) == (
        "B_02.02",
        "c0060",
        "B_07.01",
        "c0040",
    )


def test_rel_013_non_critical_service_needs_no_assessment():
    assert codes([function(critical=NO)], [service(reliance="")], []) == []


def test_rel_013_absent_b_07_01_is_not_checked():
    assert "REL-013" not in codes([function()], [service()])


def test_rel_014_assessment_without_service():
    found = finding("REL-014", [function()], [service()], [assessment(), assessment(contract="C9")])
    assert [(o.table, o.row) for o in found.occurrences] == [("B_07.01", 2)]


# ------------------------------------------------------------------ REL-015, REL-016, REL-017
def test_rel_015_reliance_reported_for_a_non_critical_function():
    found = finding("REL-015", [function(critical=NO)], [service()])
    assert [(o.column, o.value) for o in found.occurrences] == [("c0180", "eba_ZZ:x795")]


def test_rel_016_reliance_empty_for_a_critical_function():
    found = finding("REL-016", [function()], [service(reliance="")], [assessment()])
    assert [o.column for o in found.occurrences] == ["c0180"]


def test_unknown_function_is_left_to_the_reference_rules():
    """A B_02.02 row citing an undeclared function is DAT-005 (R7), not REL-015 or 016."""
    assert codes([function()], [service(), service("F9", reliance="")], [assessment()]) == []


def test_rel_017_no_exit_plan_for_a_critical_service():
    found = finding("REL-017", [function()], [service()], [assessment(exit_plan=NO)])
    assert [(o.table, o.column, o.value) for o in found.occurrences] == [("B_07.01", "c0080", NO)]


def test_rel_017_exit_plan_of_a_non_critical_service_is_not_checked():
    assert codes([function(critical=NO)], [service(reliance="")], [assessment(exit_plan=NO)]) == []


# ------------------------------------------------------------------ origin and status
EXPECTED = {
    "BUS-012": ("MAJOR", "OFFICIAL", "CONFIRMED"),
    "BUS-013": ("MAJOR", "OFFICIAL", "CONFIRMED"),
    "REL-012": ("BLOCKER", "PO_VALIDATED", "PROVISIONAL"),
    "DQ-011": ("INFO", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-015": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-016": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-017": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-012": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-013": ("INFO", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-013": ("MAJOR", "OFFICIAL", "CONFIRMED"),
    "REL-014": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-015": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-016": ("MAJOR", "OFFICIAL", "CONFIRMED"),
    "REL-017": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
}


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_severity_origin_and_status_follow_the_decisions(code):
    registry = {e["code"]: e for e in load_registry()}
    severity, origin, status = EXPECTED[code]
    assert load_catalog()[code]["severity"] == severity
    assert (registry[code]["origin"], registry[code]["severity_status"]) == (origin, status)


def test_po_validated_origin_is_never_confirmed():
    """REL-012: the PO may raise a severity, but only the authorities confirm a rejection."""
    for entry in load_registry():
        if entry["origin"] == "PO_VALIDATED":
            assert entry["severity_status"] != "CONFIRMED", entry["code"]
