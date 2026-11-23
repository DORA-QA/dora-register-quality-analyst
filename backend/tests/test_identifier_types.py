# SPDX-License-Identifier: EUPL-1.2
"""Identifier against its declared type of code (DAT-014, DAT-016 to DAT-021, DAT-034, DAT-035)."""

import pytest

from contracts import identifiers
from contracts.identifiers import lei_check_digits
from tests.test_technical_rules import frame, run_all

LEI = "DUMMYLEI1234567890" + lei_check_digits("DUMMYLEI1234567890")
LEI_T, EUID_T, CRN_T, VAT_T = (f"eba_qCO:qx200{n}" for n in (0, 2, 3, 4))
NATIONAL_T, PASSPORT_T = "eba_qCO:qx2001", "eba_qCO:qx2005"
FR, DE = "eba_GA:FR", "eba_GA:DE"
LEGAL, NATURAL = "eba_CT:x212", "eba_CT:x213"


def found(tables, code: str) -> list[str]:
    return [m.details for m in run_all(tables) if m.code == code]


def provider(**cells: str) -> dict:
    return {"B_05.01": frame("B_05.01", cells)}


@pytest.mark.parametrize(
    ("value", "declared", "expected"),
    [
        ("FR12394199723", identifiers.KIND_EUID, identifiers.KIND_VAT),
        (LEI, identifiers.KIND_OTHER, identifiers.KIND_LEI),
        ("394199723", identifiers.KIND_LEI, identifiers.KIND_CRN),
        ("FR5910.394199723", identifiers.KIND_VAT, identifiers.KIND_EUID),
        (LEI, identifiers.KIND_LEI, None),
        ("FR5910.394199723", identifiers.KIND_EUID, None),
        ("12AB34567", identifiers.KIND_OTHER, None),
        ("HRB116737", identifiers.KIND_CRN, None),
    ],
)
def test_looks_like_other_kind(value, declared, expected) -> None:
    assert identifiers.looks_like_other_kind(value, declared) == expected


def test_vat_declared_as_euid_is_one_type_error() -> None:
    tables = provider(c0010="FR12394199723", c0020=EUID_T, c0080=DE)
    codes = {m.code for m in run_all(tables)}
    assert "DAT-014" in codes
    assert not codes & {"DAT-011", "DAT-012", "DAT-013"}
    assert found(tables, "DAT-014") == ["#1 · 'FR12394199723' : EUID → VAT"]


def test_lei_declared_as_passport() -> None:
    assert found(provider(c0010=LEI, c0020=PASSPORT_T), "DAT-014") == [
        f"#1 · '{LEI}' : OTHER → LEI"
    ]


def test_siren_declared_as_lei_is_not_also_a_lei_error() -> None:
    codes = {m.code for m in run_all(provider(c0010="394199723", c0020=LEI_T))}
    assert "DAT-014" in codes and "DAT-006" not in codes


@pytest.mark.parametrize(
    ("value", "bad"),
    [
        ("FRRCSPARIS.394199723", False),
        ("FRRCSPARIS394199723", False),
        ("frrcslyon.394199723", False),
        ("FRRCS.ABC", True),
        ("FR394199723", True),
        ("FRRCSPARIS.39419972", True),
    ],
)
def test_french_euid_register_code_and_siren(value, bad) -> None:
    assert bool(found(provider(c0010=value, c0020=EUID_T, c0080=FR), "DAT-016")) is bad


@pytest.mark.parametrize(
    ("value", "bad"),
    [("394199723", False), ("39419972300015", False), ("3941997", True), ("394 199 723", True)],
)
def test_french_crn(value, bad) -> None:
    assert bool(found(provider(c0010=value, c0020=CRN_T, c0080=FR), "DAT-017")) is bad


def test_crn_of_unconfirmed_countries_is_not_checked() -> None:
    assert not found(provider(c0010="HRB 116737", c0020=CRN_T, c0080=DE), "DAT-017")
    # Poland: REGON is confirmed but KRS and NIP are not, so the country is not checked
    assert not found(provider(c0010="ABC", c0020=CRN_T, c0080="eba_GA:PL"), "DAT-017")


@pytest.mark.parametrize(
    ("country", "value", "bad"),
    [
        ("BE", "0123.456.789", False),
        ("BE", "2123456789", True),
        ("NL", "12345678", False),
        ("NL", "1234567", True),
        ("FI", "1234567-8", False),
        ("FI", "12345678", True),
        ("ES", "A12345678", False),
        ("ES", "123", True),
        ("CH", "CHE-123.456.789", False),
        ("CH", "123456789", True),
    ],
)
def test_crn_of_confirmed_countries(country, value, bad) -> None:
    tables = provider(c0010=value, c0020=CRN_T, c0080=f"eba_GA:{country}")
    assert bool(found(tables, "DAT-017")) is bad


@pytest.mark.parametrize(
    ("country", "value", "bad"),
    [
        ("DE", "DE123456789", False),
        ("DE", "DE12345678", True),
        ("GR", "EL123456789", False),
        ("GR", "GR123456789", True),
        ("BE", "BE0123456789", False),
        ("BE", "BE2123456789", True),
        ("SE", "SE123456789001", False),
    ],
)
def test_vat_of_other_countries(country, value, bad) -> None:
    tables = provider(c0010=value, c0020=VAT_T, c0080=f"eba_GA:{country}")
    assert bool(found(tables, "DAT-018")) is bad


@pytest.mark.parametrize(
    ("value", "bad"), [("FR12394199723", False), ("FR394199723", True), ("FR1239419972", True)]
)
def test_french_vat(value, bad) -> None:
    assert bool(found(provider(c0010=value, c0020=VAT_T, c0080=FR), "DAT-018")) is bad


def test_additional_code_rules() -> None:
    tables = provider(c0010="394199723", c0020=CRN_T, c0030="394199723", c0040=NATIONAL_T)
    assert found(tables, "DAT-019") == ["#1 · 'eba_qCO:qx2001'"]
    assert found(tables, "DAT-020") == ["#1 · '394199723'"]


# ------------------------------------------------------------------ type of person (PO, 02/11/2026)
@pytest.mark.parametrize("additional_type", [NATIONAL_T, PASSPORT_T])
def test_dat_019_legal_person_with_national_code_or_passport(additional_type) -> None:
    tables = provider(c0010=LEI, c0020=LEI_T, c0030="X1", c0040=additional_type, c0070=LEGAL)
    assert found(tables, "DAT-019") == [f"#1 · '{additional_type}'"]


@pytest.mark.parametrize("additional_type", [NATIONAL_T, PASSPORT_T])
def test_dat_019_natural_person_may_use_national_code_or_passport(additional_type) -> None:
    tables = provider(
        c0010="X4RTBPFW4", c0020=NATIONAL_T, c0030="X1", c0040=additional_type, c0070=NATURAL
    )
    assert found(tables, "DAT-019") == []


@pytest.mark.parametrize("additional_type", [CRN_T, VAT_T])
def test_dat_019_legal_person_with_company_or_vat_number_is_tolerated(additional_type) -> None:
    """ITS letter: LEI or EUID; EBA rule v8818_m inactive, so tolerated (decision of the PO)."""
    tables = provider(c0010=LEI, c0020=LEI_T, c0030="X1", c0040=additional_type, c0070=LEGAL)
    assert found(tables, "DAT-019") == []


def test_dat_019_empty_type_of_person_stays_strict() -> None:
    tables = provider(c0010=LEI, c0020=LEI_T, c0030="X1", c0040=PASSPORT_T)
    assert found(tables, "DAT-019") == [f"#1 · '{PASSPORT_T}'"]


@pytest.mark.parametrize(
    ("cells", "column"),
    [
        ({"c0010": "FRRCSPARIS.394199723", "c0020": EUID_T}, "c0020"),
        (
            {
                "c0010": "X4RTBPFW4",
                "c0020": NATIONAL_T,
                "c0030": "FRRCSPARIS.394199723",
                "c0040": EUID_T,
            },
            "c0040",
        ),
    ],
)
def test_dat_034_natural_person_with_an_euid(cells, column) -> None:
    messages = [m for m in run_all(provider(**cells, c0070=NATURAL)) if m.code == "DAT-034"]
    assert [m.details for m in messages] == [f"#1 · '{EUID_T}'"]
    assert [(o.table, o.column) for o in messages[0].occurrences] == [("B_05.01", column)]


def test_dat_035_natural_person_with_a_lei_is_an_information() -> None:
    tables = provider(c0010=LEI, c0020=LEI_T, c0070=NATURAL)
    assert found(tables, "DAT-035") == [f"#1 · '{LEI_T}'"]
    assert found(tables, "DAT-034") == []


def test_legal_person_with_lei_or_euid_raises_neither_dat_034_nor_dat_035() -> None:
    tables = provider(
        c0010=LEI, c0020=LEI_T, c0030="FRRCSPARIS.394199723", c0040=EUID_T, c0070=LEGAL
    )
    codes = {m.code for m in run_all(tables)}
    assert not codes & {"DAT-034", "DAT-035"}


def test_type_without_code_is_not_reported_for_a_natural_person() -> None:
    tables = provider(c0010="X4RTBPFW4", c0020=NATIONAL_T, c0040=EUID_T, c0070=NATURAL)
    assert found(tables, "DAT-034") == []


def test_branch_code_equal_to_head_office() -> None:
    tables = {
        "B_01.03": frame(
            "B_01.03", {"c0010": LEI, "c0020": LEI}, {"c0010": "SUCC-01", "c0020": LEI}
        )
    }
    assert found(tables, "DAT-021") == [f"#1 · '{LEI}'"]
