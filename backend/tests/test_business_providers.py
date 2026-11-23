# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 2: ICT providers (REL-006, REL-007, DQ-001 to DQ-004).

For each check (brief §17.1): compliant case, non-compliant case, limit case, absent table,
empty value, documented exception, location of the occurrences, origin and status.
"""

import pytest

from contracts.check_report import load_registry
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import load_catalog
from rules.business.providers import company_key, provider_rules, siren_of
from rules.engine import RulesEngine
from tests.test_technical_rules import frame

LEI_A, LEI_B = "529900KIWVWB8P3VEK25", "5299001KGZ7JIYCF3247"
LEI, EUID, CRN, NATIONAL = "eba_qCO:qx2000", "eba_qCO:qx2002", "eba_qCO:qx2003", "eba_qCO:qx2001"
LEGAL, NATURAL = "eba_CT:x212", "eba_CT:x213"


def provider(
    code, kind=LEI, name="PRESTA", country="eba_GA:FR", person=LEGAL, parent=None, extra=None
):
    return {
        "c0010": code,
        "c0020": kind,
        "c0030": (extra or ("", ""))[0],
        "c0040": (extra or ("", ""))[1],
        "c0050": name,
        "c0060": name,
        "c0070": person,
        "c0080": country,
        "c0110": parent or code,
        "c0120": kind,
    }


def used(*codes, kind=LEI):
    """B_02.02 rows using the providers (one contract each)."""
    return [{"c0010": f"C{i}", "c0030": code, "c0040": kind} for i, code in enumerate(codes)]


def run(b0501, b0202=None, **others):
    found = {"B_05.01": frame("B_05.01", *b0501)}
    if b0202 is not None:
        found["B_02.02"] = frame("B_02.02", *b0202)
    for table, rows in others.items():
        code = f"{table[:4]}.{table[5:]}"  # B_05_02 -> B_05.02
        found[code] = frame(code, *rows)
    return RulesEngine(provider_rules()).run(RoIDataset("ZIP", PackageMetadata(), found)).messages


def codes(*args, **kwargs):
    return sorted(m.code for m in run(*args, **kwargs))


def finding(code, *args, **kwargs):
    return next(m for m in run(*args, **kwargs) if m.code == code)


# ------------------------------------------------------------------ helpers
def test_company_key_removes_legal_forms_and_punctuation():
    assert (
        company_key("MICROSOFT FRANCE")
        == company_key("Microsoft France S.A.S.")
        == "microsoft france"
    )
    assert company_key("Société Générale SA") == "societe generale"
    assert company_key("Sas Conseil") == "conseil"


@pytest.mark.parametrize(
    ("code", "siren"),
    [
        ("552032534", "552032534"),
        ("55203253400016", "552032534"),
        ("FR12552032534", "552032534"),
        ("FRRCSPARIS.552032534", "552032534"),
        (LEI_A, None),
    ],
)
def test_siren_of(code, siren):
    assert siren_of(code) == siren


# ------------------------------------------------------------------ compliant and absent
def test_consistent_providers_raise_nothing():
    assert codes([provider(LEI_A, name="A"), provider(LEI_B, name="B")], used(LEI_A, LEI_B)) == []


def test_absent_tables_raise_nothing():
    assert (
        RulesEngine(provider_rules()).run(RoIDataset("ZIP", PackageMetadata(), {})).messages == []
    )


# ------------------------------------------------------------------ REL-006
def test_rel_006_type_repeated_differently_gives_both_sides():
    found = finding("REL-006", [provider(LEI_A)], used(LEI_A, kind=CRN))
    source, target = found.occurrences
    assert (source.table, source.row, source.column, source.value) == ("B_02.02", 1, "c0040", CRN)
    assert (source.target_table, source.target_column, source.side) == (
        "B_05.01",
        "c0020",
        "source",
    )
    assert (target.table, target.column, target.value, target.side) == (
        "B_05.01",
        "c0020",
        LEI,
        "target",
    )


def test_rel_006_checks_every_repeated_column():
    b0502 = [{"c0010": "C0", "c0030": LEI_A, "c0040": LEI, "c0060": LEI_A, "c0070": CRN}]
    b0701 = [{"c0010": "C0", "c0020": LEI_A, "c0030": CRN}]
    found = [
        m
        for m in run([provider(LEI_A)], used(LEI_A), B_05_02=b0502, B_07_01=b0701)
        if m.code == "REL-006"
    ]
    assert sorted(m.params["table"] for m in found) == ["B_05.02", "B_07.01"]


def test_rel_006_unknown_provider_or_empty_type_left_to_other_rules():
    assert codes([provider(LEI_A)], [{"c0010": "C0", "c0030": "INCONNU", "c0040": CRN}]) == [
        "DQ-004"
    ]
    assert "REL-006" not in codes([provider(LEI_A)], used(LEI_A, kind=""))


# ------------------------------------------------------------------ REL-007
def test_rel_007_direct_legal_person_without_lei_or_euid():
    found = finding("REL-007", [provider("552032534", kind=CRN)], used("552032534", kind=CRN))
    (place,) = found.occurrences
    assert (place.table, place.column, place.value) == ("B_05.01", "c0020", CRN)
    # E13: the occurrence names the column that requires a LEI or an EUID.
    assert (place.target_table, place.target_column) == ("B_05.01", "c0070")


def test_rel_007_exceptions_natural_person_and_euid():
    natural = provider("X4RTBPFW4", kind=NATIONAL, person=NATURAL)
    euid = provider("FRRCSPARIS.552032534", kind=EUID)
    found = codes([natural, euid], used("X4RTBPFW4", "FRRCSPARIS.552032534"))
    assert "REL-007" not in found


def test_rel_007_covers_subcontractors_and_ultimate_parents():
    """Every legal person of B_05.01 since 0.8.1, not only the direct providers (PO, 02/11)."""
    direct = provider(LEI_A, parent="394199723")
    subcontractor = provider("552032534", kind=CRN, name="SOUS-TRAITANT")
    parent = provider("394199723", kind=CRN, name="MERE")
    found = finding(
        "REL-007",
        [direct, subcontractor, parent],
        used(LEI_A),
        B_05_02=[{"c0010": "C0", "c0030": "552032534"}],
    )
    assert sorted(o.value for o in found.occurrences) == [CRN, CRN]
    assert {o.row for o in found.occurrences} == {2, 3}


# ------------------------------------------------------------------ DQ-001, DQ-002, DQ-003
def test_dq_001_same_name_and_country_different_codes():
    b0501 = [
        provider(LEI_A, name="MICROSOFT FRANCE"),
        provider("552032534", kind=CRN, name="Microsoft France S.A.S."),
    ]
    found = finding("DQ-001", b0501, used(LEI_A, "552032534"))
    assert [o.value for o in found.occurrences] == [LEI_A, "552032534"]


def test_dq_001_same_name_in_two_countries_is_legitimate():
    b0501 = [provider(LEI_A, name="ACME"), provider(LEI_B, name="ACME", country="eba_GA:DE")]
    assert codes(b0501, used(LEI_A, LEI_B)) == []


def test_dq_001_uses_the_latin_name_first():
    first = provider(LEI_A, name="ACME")
    second = {**provider(LEI_B, name="АКМЕ"), "c0060": "Acme"}
    assert "DQ-001" in codes([first, second], used(LEI_A, LEI_B))


def test_dq_002_additional_code_of_one_is_the_main_code_of_another():
    b0501 = [
        provider(LEI_A, name="A"),
        provider("552032534", kind=CRN, name="B", extra=(LEI_A, LEI)),
    ]
    found = finding("DQ-002", b0501, used(LEI_A, "552032534"))
    assert [(o.row, o.column, o.side) for o in found.occurrences] == [
        (2, "c0030", "source"),
        (1, "c0010", "target"),
    ]


def test_dq_003_french_euid_containing_the_siren_of_another_provider():
    b0501 = [
        provider("FRRCSPARIS.552032534", kind=EUID, name="A"),
        provider("552032534", kind=CRN, name="B"),
    ]
    found = finding("DQ-003", b0501, used("FRRCSPARIS.552032534", "552032534"))
    assert [o.value for o in found.occurrences] == ["FRRCSPARIS.552032534", "552032534"]


# ------------------------------------------------------------------ DQ-004
def test_dq_004_unused_provider_but_not_an_ultimate_parent():
    b0501 = [
        provider(LEI_A, name="A", parent=LEI_B),
        provider(LEI_B, name="MERE"),
        provider("ISOLE", kind=CRN, name="I"),
    ]
    found = finding("DQ-004", b0501, used(LEI_A))
    assert [o.value for o in found.occurrences] == ["ISOLE"]


def test_dq_004_a_subcontractor_of_a_chain_is_used():
    b0501 = [provider(LEI_A, name="A"), provider(LEI_B, name="SOUS-TRAITANT")]
    assert (
        codes(b0501, used(LEI_A), B_05_02=[{"c0010": "C0", "c0030": LEI_B, "c0060": LEI_A}]) == []
    )


# ------------------------------------------------------------------ origin and status
EXPECTED = {
    "REL-006": ("BLOCKER", "OFFICIAL", "PROVISIONAL"),
    "REL-007": ("MINOR", "OFFICIAL", "CONFIRMED"),
    "DQ-001": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-002": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-003": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "DQ-004": ("INFO", "PO_VALIDATED", "PO_VALIDATED"),
}


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_severity_origin_and_status_follow_the_decisions(code):
    registry = {e["code"]: e for e in load_registry()}
    severity, origin, status = EXPECTED[code]
    assert load_catalog()[code]["severity"] == severity
    assert (registry[code]["origin"], registry[code]["severity_status"]) == (origin, status)
