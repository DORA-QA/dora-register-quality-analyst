# SPDX-License-Identifier: EUPL-1.2
"""LEI (ISO 17442) and EUID: pure functions, then the rules on the dataset."""

import pytest

from contracts import data_model, identifiers
from contracts.identifiers import (
    EUID_BAD_CHARACTERS,
    EUID_BAD_PREFIX,
    EUID_EMPTY_PART,
    EUID_OK,
    EUID_WHITESPACE,
    LEI_BAD_CHARACTERS,
    LEI_BAD_CHECKSUM,
    LEI_BAD_MASK,
    LEI_LENGTH_WRONG,
    LEI_OK,
    analyse_euid,
    analyse_lei,
    lei_check_digits,
    lei_checksum_is_valid,
)
from contracts.messages import Severity, has_blocker
from tests.test_technical_rules import frame, run_all

# Identifiers published by their holders, used only as check-digit vectors.
PUBLISHED_LEIS = ["5493001KJTIIGC8Y1R12", "7ZW8QJWVPR4P1J1KQY45", "HWUPKR0MPOU8FGXBT394"]


def lei(prefix: str) -> str:
    return prefix + lei_check_digits(prefix)


VALID = lei("DUMMYLEI1234567890")
LEI_TYPE = "eba_qCO:qx2000"
EUID_TYPE = "eba_qCO:qx2002"


@pytest.mark.parametrize("value", PUBLISHED_LEIS + [VALID, lei("ABCDEFGHIJKLMNOPQR")])
def test_valid_lei(value: str) -> None:
    assert lei_checksum_is_valid(value)
    assert analyse_lei(value).problem == LEI_OK


def test_check_digits_follow_iso_7064_mod_97_10() -> None:
    assert lei_check_digits("5493001KJTIIGC8Y1R") == "12"
    assert lei_check_digits("7ZW8QJWVPR4P1J1KQY") == "45"
    # Any single-character change breaks the check.
    assert not lei_checksum_is_valid("5493001KJTIIGC8Y1R13")
    assert analyse_lei("5493001KJTIIGC8Y1R13").problem == LEI_BAD_CHECKSUM


@pytest.mark.parametrize(
    ("value", "problem"),
    [
        ("5493001KJTIIGC8Y1R1", LEI_LENGTH_WRONG),
        ("5493001KJTIIGC8Y1R123", LEI_LENGTH_WRONG),
        ("5493001kjtiigc8y1r12", LEI_BAD_CHARACTERS),
        ("5493001KJTIIGC8Y-R12", LEI_BAD_CHARACTERS),
        ("5493001KJTIIGC8Y1RAB", LEI_BAD_MASK),
        ("5493001KJTIIGC8Y1R13", LEI_BAD_CHECKSUM),
    ],
)
def test_lei_problems_are_found_in_a_fixed_order(value: str, problem: str) -> None:
    assert analyse_lei(value).problem == problem


def test_the_mask_is_checked_before_the_check_digits() -> None:
    # Letters in the last two positions: no modulo calculation, no misleading "bad key" answer.
    assert not lei_checksum_is_valid("5493001KJTIIGC8Y1RAB")
    assert analyse_lei("5493001KJTIIGC8Y1RAB").problem == LEI_BAD_MASK


def test_empty_and_odd_values_never_raise() -> None:
    assert analyse_lei("").problem == LEI_LENGTH_WRONG
    assert analyse_lei("   ").problem == LEI_LENGTH_WRONG
    assert analyse_lei("É" * 20).problem == LEI_BAD_CHARACTERS
    assert not lei_checksum_is_valid("")


def test_whitespace_is_described_without_changing_the_value() -> None:
    value = f"  {PUBLISHED_LEIS[0]} "
    analysis = analyse_lei(value)

    assert (analysis.leading_spaces, analysis.trailing_spaces, analysis.inner_spaces) == (
        True,
        True,
        False,
    )
    # The other checks are made on the value without spaces: it is valid here.
    assert analysis.problem == LEI_OK
    assert analysis.normalized == PUBLISHED_LEIS[0]
    assert analyse_lei("5493001KJTIIGC 8Y1R12").inner_spaces is True


@pytest.mark.parametrize(
    ("value", "problem", "country"),
    [
        ("DEK1101R.HRB116737", EUID_OK, "DE"),
        ("frrcs.123456789", EUID_OK, "FR"),
        ("DEK1101R.HRB 116737", EUID_WHITESPACE, None),
        (" DEK1101R.HRB116737", EUID_WHITESPACE, None),
        ("HRB116737", EUID_OK, "HR"),
        ("FR394199723", EUID_OK, "FR"),
        ("FR.394199723", EUID_EMPTY_PART, None),
        ("FR", EUID_EMPTY_PART, None),
        ("DEK1101R.HRB.1", EUID_EMPTY_PART, None),
        ("FR-394199723", EUID_BAD_CHARACTERS, None),
        (".HRB116737", EUID_BAD_PREFIX, None),
        ("DEK1101R.", EUID_EMPTY_PART, None),
        ("1ER.123", EUID_BAD_PREFIX, None),
        ("D.123", EUID_BAD_PREFIX, None),
    ],
)
def test_euid_syntax(value: str, problem: str, country: str | None) -> None:
    analysis = analyse_euid(value)
    assert (analysis.problem, analysis.country) == (problem, country)


# ------------------------------------------------------------ rules on a dataset
def codes(messages) -> list[str]:
    return sorted(m.code for m in messages if m.code >= "DAT-006")


def test_identifier_columns_come_from_the_reference() -> None:
    fields = data_model.identifier_fields()
    assert ("B_01.01", "c0010") in fields.lei_columns
    assert ("B_05.01", "c0010", "c0020") in fields.typed
    assert "FR" in data_model.eea_countries()
    assert "US" not in data_model.eea_countries()


def test_a_valid_lei_gives_no_finding() -> None:
    tables = {"B_01.01": frame("B_01.01", {"c0010": VALID})}

    assert codes(run_all(tables)) == []


def test_each_lei_problem_has_its_own_finding_and_severity() -> None:
    rows = [
        {"c0010": "SHORT"},
        {"c0010": VALID.lower()},
        {"c0010": "ABCDEFGHIJKLMNOPQRAB"},
        {"c0010": VALID[:-1] + ("0" if VALID[-1] != "0" else "1")},
        {"c0010": f" {VALID}"},
    ]
    messages = run_all({"B_01.02": frame("B_01.02", *rows)})
    by_code = {m.code: m for m in messages if m.code >= "DAT-006"}

    assert sorted(by_code) == ["DAT-006", "DAT-007", "DAT-008", "DAT-009", "DAT-010"]
    assert by_code["DAT-006"].details == "#1 · 'SHORT'"
    assert by_code["DAT-007"].severity is Severity.MAJOR
    assert by_code["DAT-009"].severity is Severity.MAJOR
    assert by_code["DAT-009"].params["leading"] == 1
    assert by_code["DAT-010"].params["count"] == 1
    # The raw value stays in the finding, with its space.
    assert by_code["DAT-009"].details == f"#5 · ' {VALID}'"


def test_lei_empty_values_are_left_to_the_mandatory_check() -> None:
    tables = {
        "B_01.02": frame("B_01.02", {"c0010": VALID}, {"c0010": VALID[:-2] + "00", "c0060": ""})
    }

    assert [m.code for m in run_all(tables) if m.code >= "DAT-006"] == ["DAT-010"]


def test_typed_identifier_is_checked_only_when_declared_as_lei() -> None:
    row = {"c0010": "NOT-A-LEI", "c0020": LEI_TYPE}
    other = {"c0010": "NATIONAL-CODE-1", "c0020": "eba_qCO:qx2001"}
    untyped = {"c0010": "ANYTHING", "c0020": ""}

    messages = run_all({"B_05.01": frame("B_05.01", row, other, untyped)})

    assert codes(messages) == ["DAT-006"]
    assert messages[0].details == "#1 · 'NOT-A-LEI'"


def test_euid_findings_separate_syntax_and_country() -> None:
    rows = [
        {"c0010": "DEK1101R.HRB116737", "c0020": EUID_TYPE},
        {"c0010": "HRB 116737", "c0020": EUID_TYPE},
        {"c0010": "USDE.12345", "c0020": EUID_TYPE},
        {"c0010": "HRB 1", "c0020": "eba_qCO:qx2001"},
    ]
    messages = run_all({"B_05.01": frame("B_05.01", *rows)})
    by_code = {m.code: m for m in messages if m.code >= "DAT-011"}

    assert sorted(by_code) == ["DAT-011", "DAT-012"]
    assert by_code["DAT-011"].details == "#2 · 'HRB 116737'"
    assert by_code["DAT-012"].details == "#3 · 'USDE.12345'"


def test_tables_outside_the_reference_are_ignored() -> None:
    found = codes(run_all({"B_99.01": frame("B_01.01", {"c0010": "x"})}))
    assert [code for code in found if code != "DAT-030"] == []


def test_findings_are_grouped_by_table_and_column() -> None:
    tables = {
        "B_01.02": frame("B_01.02", {"c0010": "BAD1", "c0060": "BAD2"}),
        "B_01.01": frame("B_01.01", {"c0010": "BAD3"}),
    }
    places = sorted(
        (m.params["table"], m.params["column"]) for m in run_all(tables) if m.code == "DAT-006"
    )

    assert places == [
        ("B_01.01", "B_01.01.0010"),
        ("B_01.02", "B_01.02.0010"),
        ("B_01.02", "B_01.02.0060"),
    ]


def test_euid_prefix_must_match_headquarters_country() -> None:
    rows = [
        {"c0010": "FR394199723", "c0020": EUID_TYPE, "c0080": "eba_GA:FR"},
        {"c0010": "DEK1101R.HRB1", "c0020": EUID_TYPE, "c0080": "eba_GA:FR"},
        {"c0010": "EL123456", "c0020": EUID_TYPE, "c0080": "eba_GA:GR"},
        {"c0010": "394199723", "c0020": "eba_qCO:qx2003", "c0080": "eba_GA:DE"},
        {"c0010": "FR394199723", "c0020": EUID_TYPE, "c0080": ""},
    ]
    messages = [m for m in run_all({"B_05.01": frame("B_05.01", *rows)}) if m.code == "DAT-013"]

    assert [m.details for m in messages] == ["#2 · 'DEK1101R.HRB1' ≠ FR"]


def test_euid_without_dot_is_reported_as_information() -> None:
    """PO-24 (#94): Regulation 2021/1042 imposes no separator; the dot is advised by the EBA."""
    rows = [
        {"c0010": "DEK1101R.HRB116737", "c0020": EUID_TYPE},  # dot: nothing to say
        {"c0010": "FR394199723", "c0020": EUID_TYPE},  # valid syntax, no dot
        {"c0010": "HRB 116737", "c0020": EUID_TYPE},  # syntax error: DAT-011 only
        {"c0010": "NODOT123", "c0020": "eba_qCO:qx2001"},  # not declared as an EUID
    ]
    messages = [m for m in run_all({"B_05.01": frame("B_05.01", *rows)}) if m.code == "DAT-031"]

    assert len(messages) == 1
    assert messages[0].severity is Severity.INFO
    assert messages[0].details == "#2 · 'FR394199723'"
    assert not has_blocker(messages)


def test_registry_separator() -> None:
    assert identifiers.has_registry_separator("DEK1101R.HRB116737")
    assert not identifiers.has_registry_separator("FR394199723")


def test_several_findings_on_one_same_value_keep_the_raw_value() -> None:
    """Brief §9.2 and epic 6: a LEI with a space is reported twice, on the same raw value."""
    raw = " " + VALID[:-1]  # leading space and 19 significant characters
    messages = run_all({"B_05.01": frame("B_05.01", {"c0010": raw, "c0020": LEI_TYPE})})
    places = {
        m.code: {(o.table, o.row, o.column, o.value) for o in m.occurrences}
        for m in messages
        if m.code in ("DAT-006", "DAT-009")
    }

    assert set(places) == {"DAT-006", "DAT-009"}
    assert places["DAT-006"] == places["DAT-009"] == {("B_05.01", 1, "c0010", raw)}
