# SPDX-License-Identifier: EUPL-1.2
"""B_02.01.0030 doit citer un accord-cadre (eba_CO:x2) : DAT-029, bloquant (PO, issue #76)."""

from tests.test_technical_rules import frame, run_all

ROWS = {
    "framework": {"c0010": "CADRE", "c0020": "eba_CO:x2"},
    "single": {"c0010": "UNIQUE", "c0020": "eba_CO:x1"},
}


def found(*rows: dict[str, str]):
    return [m for m in run_all({"B_02.01": frame("B_02.01", *rows)}) if m.code == "DAT-029"]


def test_reference_to_a_framework_is_accepted() -> None:
    row = {"c0010": "SUBSEQ", "c0020": "eba_CO:x3", "c0030": "CADRE"}
    assert found(ROWS["framework"], row) == []


def test_reference_to_another_type_is_reported() -> None:
    row = {"c0010": "SUBSEQ", "c0020": "eba_CO:x3", "c0030": "UNIQUE"}
    messages = found(ROWS["single"], row)
    assert [m.details for m in messages] == ["#2 · 'UNIQUE' (eba_CO:x1)"]
    assert messages[0].severity.name == "BLOCKER"


def test_reference_to_a_contract_without_type_is_reported() -> None:
    row = {"c0010": "SUBSEQ", "c0020": "eba_CO:x3", "c0030": "SANSTYPE"}
    assert len(found({"c0010": "SANSTYPE"}, row)) == 1


def test_unknown_contract_is_left_to_the_foreign_key() -> None:
    row = {"c0010": "SUBSEQ", "c0020": "eba_CO:x3", "c0030": "INCONNU"}
    assert found(ROWS["framework"], row) == []


def test_empty_reference_is_not_a_reference() -> None:
    assert found(ROWS["single"], {"c0010": "AUTRE", "c0020": "eba_CO:x1"}) == []
