# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 1: entities of the group and ultimate parents (REL-001 to 005, BUS-001 to 005).

For each check (brief §17.1): compliant case, non-compliant case, limit case, absent table,
empty value, documented exception, location of the occurrences, origin and status.
"""

import polars as pl
import pytest

from contracts.check_report import load_registry
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import load_catalog
from rules.business.common import normalise_name
from rules.business.entities import entity_rules
from rules.engine import RulesEngine
from tests.test_technical_rules import frame

EF, TOP, IG, FE2 = (
    "529900P784EKW7VFMQ21",
    "529900R81VAA8RCKLQ52",
    "5299003U9L1RY87FL751",
    "529900WFW9ZXG409UL36",
)
LEI = "eba_qCO:qx2000"


def entity(
    lei,
    name="ENTITE",
    country="eba_GA:FR",
    kind="eba_CT:x316",
    rank="eba_RP:x56",
    parent=TOP,
    **dates,
):
    return {
        "c0010": lei,
        "c0020": name,
        "c0030": country,
        "c0040": kind,
        "c0050": rank,
        "c0060": parent,
        "c0070": dates.get("update", "2026-10-19"),
        "c0080": dates.get("integration", "2026-10-01"),
        "c0090": dates.get("deletion", "9999-12-31"),
    }


def provider(code, name="ENTITE", country="eba_GA:FR", kind=LEI, parent=None, parent_kind=LEI):
    return {
        "c0010": code,
        "c0020": kind,
        "c0050": name,
        "c0060": name,
        "c0070": "eba_CT:x212",
        "c0080": country,
        "c0110": parent or code,
        "c0120": parent_kind,
    }


def group(*entities):
    """A consistent group: TOP (x53) above EF, which maintains the register."""
    return entities or (
        entity(TOP, "MERE", rank="eba_RP:x53", parent=TOP),
        entity(EF, "EF", rank="eba_RP:x551", parent=TOP),
    )


def tables(b0102=None, b0501=None, b0101=None):
    found = {
        "B_01.01": frame("B_01.01", b0101 or {"c0010": EF, "c0020": "EF", "c0030": "eba_GA:FR"}),
        "B_01.02": frame("B_01.02", *(b0102 or group())),
    }
    if b0501 is not None:
        found["B_05.01"] = frame("B_05.01", *b0501)
    return found


def run(found: dict[str, pl.DataFrame]):
    return RulesEngine(entity_rules()).run(RoIDataset("ZIP", PackageMetadata(), found)).messages


def codes(found) -> list[str]:
    return sorted(m.code for m in run(found))


def finding(found, code):
    return next(m for m in run(found) if m.code == code)


# ------------------------------------------------------------------ compliant
def test_a_consistent_group_raises_nothing():
    b0501 = [provider(EF, "EF"), provider("PRESTA", "PRESTA", parent="PRESTA")]
    assert codes(tables(b0501=b0501)) == []


def test_absent_tables_raise_nothing():
    assert run({}) == []
    assert codes({"B_01.01": tables()["B_01.01"]}) == []


def test_name_normalisation():
    assert normalise_name("Caisse des Dépôts") == normalise_name("CAISSE DES DEPOTS")
    assert normalise_name("S.A.S.  Fictive-Société") == "s a s fictive societe"
    assert normalise_name("Caisse des dépôts et consignations") != normalise_name(
        "CAISSE DES DEPOTS"
    )


# ------------------------------------------------------------------ REL-001
def test_rel_001_entity_of_the_register_missing_from_b_01_02():
    found = finding(
        tables(b0101={"c0010": "AUTRELEI", "c0020": "EF", "c0030": "eba_GA:FR"}), "REL-001"
    )
    (place,) = found.occurrences
    assert (place.table, place.row, place.column, place.value) == (
        "B_01.01",
        1,
        "c0010",
        "AUTRELEI",
    )
    assert (place.target_table, place.target_column, place.side) == ("B_01.02", "c0010", "source")


def test_rel_001_empty_lei_is_left_to_the_mandatory_rules():
    assert "REL-001" not in codes(tables(b0101={"c0010": "", "c0020": "EF"}))


# ------------------------------------------------------------------ REL-002, 003, 004
def test_rel_002_different_name_gives_both_sides():
    found = finding(tables(b0101={"c0010": EF, "c0020": "AUTRE", "c0030": "eba_GA:FR"}), "REL-002")
    source, target = found.occurrences
    assert (source.table, source.column, source.value, source.side) == (
        "B_01.01",
        "c0020",
        "AUTRE",
        "source",
    )
    assert (source.target_table, source.target_column) == ("B_01.02", "c0020")
    assert (target.table, target.row, target.column, target.value, target.side) == (
        "B_01.02",
        2,
        "c0020",
        "EF",
        "target",
    )


def test_rel_003_same_name_written_differently_is_an_advice():
    found = tables(b0101={"c0010": EF, "c0020": "Ef", "c0030": "eba_GA:FR"})
    assert codes(found) == ["REL-003"]


def test_rel_004_country_differs_between_b_01_02_and_b_05_01():
    found = finding(tables(b0501=[provider(EF, "EF", country="eba_GA:DE")]), "REL-004")
    assert found.params["table"] == "B_01.02" and found.params["target"] == "B_05.01"
    assert [(o.table, o.value) for o in found.occurrences] == [
        ("B_01.02", "eba_GA:FR"),
        ("B_05.01", "eba_GA:DE"),
    ]


def test_rel_002_ignores_an_empty_name():
    assert codes(tables(b0101={"c0010": EF, "c0020": "", "c0030": "eba_GA:FR"})) == []


# ------------------------------------------------------------------ BUS-001, BUS-002
def test_bus_001_two_ultimate_parents():
    b0102 = group(
        entity(TOP, "MERE", rank="eba_RP:x53", parent=TOP),
        entity(EF, "EF", rank="eba_RP:x53", parent=TOP),
    )
    found = finding(tables(b0102=b0102), "BUS-001")
    assert [o.row for o in found.occurrences] == [1, 2]


def test_bus_002_cycle_of_direct_parents():
    b0102 = group(
        entity(TOP, "MERE", rank="eba_RP:x53", parent=TOP),
        entity(EF, "EF", parent=FE2),
        entity(FE2, "FE2", parent=EF),
    )
    found = finding(tables(b0102=b0102), "BUS-002")
    assert sorted(o.value for o in found.occurrences) == [EF, FE2]


def test_bus_002_self_parent_allowed_only_for_the_ultimate_parent():
    b0102 = group(
        entity(TOP, "MERE", rank="eba_RP:x53", parent=TOP),
        entity(EF, "EF", parent=EF),
    )
    assert codes(tables(b0102=b0102)) == ["BUS-002"]


def test_bus_002_unknown_or_empty_parent_left_to_other_rules():
    b0102 = group(
        entity(TOP, "MERE", rank="eba_RP:x53", parent=TOP),
        entity(EF, "EF", parent="INCONNU"),
        entity(FE2, "FE2", parent=""),
    )
    assert codes(tables(b0102=b0102)) == []


# ------------------------------------------------------------------ REL-005, BUS-003, BUS-004
def _intra_group(ultimate):
    b0102 = (*group(), entity(IG, "IG", kind="eba_CT:x317", rank="eba_RP:x210", parent=EF))
    b0501 = [
        provider(IG, "IG", parent=ultimate),
        provider(EF, "EF"),
        provider(TOP, "MERE"),
        provider("AUTRE", "AUTRE"),
    ]
    return tables(b0102=b0102, b0501=b0501)


@pytest.mark.parametrize("ultimate", [EF, TOP])
def test_rel_005_head_of_sub_group_or_ultimate_parent_accepted(ultimate):
    """PO, 29/10: in a sub-consolidated register the head of the sub-group is accepted."""
    assert codes(_intra_group(ultimate)) == []


def test_rel_005_parent_outside_the_chain():
    found = finding(_intra_group("AUTRE"), "REL-005")
    assert [(o.table, o.column, o.side) for o in found.occurrences] == [
        ("B_05.01", "c0110", "source"),
        ("B_01.02", "c0060", "target"),
    ]


def test_bus_003_type_of_the_ultimate_parent():
    b0501 = [
        provider("FILLE", "FILLE", parent="MERE", parent_kind="eba_qCO:qx2003"),
        provider("MERE", "MERE"),
    ]
    found = finding(tables(b0501=b0501), "BUS-003")
    assert [(o.column, o.value) for o in found.occurrences] == [
        ("c0120", "eba_qCO:qx2003"),
        ("c0020", LEI),
    ]


def test_bus_004_ultimate_parent_not_its_own_ultimate_parent_reported_once():
    b0501 = [
        provider("FILLE1", "FILLE1", parent="MERE"),
        provider("FILLE2", "FILLE2", parent="MERE"),
        provider("MERE", "MERE", parent="AUTRE"),
        provider("AUTRE", "AUTRE"),
    ]
    found = finding(tables(b0501=b0501), "BUS-004")
    assert [(o.row, o.value) for o in found.occurrences] == [(3, "AUTRE")]


def test_parent_missing_from_b_05_01_is_left_to_dat_005():
    assert codes(tables(b0501=[provider("FILLE", "FILLE", parent="ABSENTE")])) == []


# ------------------------------------------------------------------ BUS-005
def test_bus_005_dates_of_the_entities():
    b0102 = group(
        entity(TOP, "MERE", rank="eba_RP:x53", parent=TOP),
        entity(EF, "EF", integration="2026-12-01"),
        entity(FE2, "FE2", deletion="2020-01-01"),
    )
    found = finding(tables(b0102=b0102), "BUS-005")
    assert [(o.row, o.column) for o in found.occurrences] == [(2, "c0080"), (3, "c0090")]


def test_bus_005_open_deletion_date_is_fine():
    b0102 = group(
        entity(TOP, "MERE", rank="eba_RP:x53", parent=TOP, deletion="9999-12-31"),
        entity(EF, "EF", deletion="2027-01-01"),
    )
    assert codes(tables(b0102=b0102)) == []


# ------------------------------------------------------------------ origin and status
EXPECTED = {
    "REL-001": ("MAJOR", "OFFICIAL", "CONFIRMED"),
    "REL-002": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-003": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-004": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-005": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-001": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-002": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-003": ("MAJOR", "OFFICIAL", "CONFIRMED"),
    "BUS-004": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-005": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
}


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_severity_origin_and_status_follow_the_decisions(code):
    registry = {e["code"]: e for e in load_registry()}
    severity, origin, status = EXPECTED[code]
    assert load_catalog()[code]["severity"] == severity
    assert (registry[code]["origin"], registry[code]["severity_status"]) == (origin, status)
    assert registry[code]["source_tables"]
