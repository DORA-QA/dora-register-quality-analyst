# SPDX-License-Identifier: EUPL-1.2
"""B_04.01.0040: key column mandatory only for a branch (DAT-027), PO decision, issue #48."""

from tests.test_technical_rules import frame, run_all

LEI = "529900P784EKW7VFMQ21"
BRANCH, NOT_BRANCH = "eba_ZZ:x838", "eba_ZZ:x839"


def codes(*rows) -> list[str]:
    return [m.code for m in run_all({"B_04.01": frame("B_04.01", *rows)})]


def test_not_a_branch_with_empty_code_is_a_minor_finding() -> None:
    found = codes({"c0010": "C1", "c0020": LEI, "c0030": NOT_BRANCH})
    assert "DAT-003" not in found and "DAT-027" not in found
    assert "DAT-028" in found


def test_not_a_branch_with_not_applicable_is_accepted() -> None:
    for text in ("Not Applicable", " not applicable "):
        found = codes({"c0010": "C1", "c0020": LEI, "c0030": NOT_BRANCH, "c0040": text})
        assert not {"DAT-003", "DAT-027", "DAT-028"} & set(found)


def test_branch_with_not_applicable_is_a_missing_code() -> None:
    found = codes({"c0010": "C1", "c0020": LEI, "c0030": BRANCH, "c0040": "Not Applicable"})
    assert "DAT-027" in found


def test_branch_without_code_is_reported() -> None:
    rows = [
        {"c0010": "C1", "c0020": LEI, "c0030": NOT_BRANCH},
        {"c0010": "C2", "c0020": LEI, "c0030": BRANCH},
    ]
    messages = [m for m in run_all({"B_04.01": frame("B_04.01", *rows)}) if m.code == "DAT-027"]
    assert [m.details for m in messages] == ["#2"]
    assert "DAT-003" not in codes(*rows)


def test_branch_with_code_is_accepted() -> None:
    found = codes({"c0010": "C1", "c0020": LEI, "c0030": BRANCH, "c0040": "BR1"})
    assert "DAT-027" not in found


def test_other_key_columns_stay_mandatory() -> None:
    assert "DAT-003" in codes({"c0010": "", "c0020": LEI, "c0030": NOT_BRANCH})


def test_duplicates_are_found_with_an_empty_branch_code() -> None:
    row = {"c0010": "C1", "c0020": LEI, "c0030": NOT_BRANCH}
    assert "DAT-004" in codes(row, dict(row))
