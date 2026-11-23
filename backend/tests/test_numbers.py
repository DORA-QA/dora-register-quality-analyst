# SPDX-License-Identifier: EUPL-1.2
"""Decimals suffix in numeric cells (DAT-015) and accuracy parameters (PKG-023)."""

import pytest

from tests.test_technical_rules import frame, run_all


def codes(tables) -> list[str]:
    return [m.code for m in run_all(tables) if m.code == "DAT-015"]


@pytest.mark.parametrize("value", ["78920030d-4", "1234D2", "10d0", "-5d-3"])
def test_suffix_is_reported(value: str) -> None:
    tables = {"B_05.01": frame("B_05.01", {"c0010": "FR1", "c0100": value})}
    assert codes(tables) == ["DAT-015"]


@pytest.mark.parametrize("value", ["78920030", "-12.5", "0", "", "1e5", "abc", "d-4"])
def test_plain_numbers_are_not_reported(value: str) -> None:
    tables = {"B_05.01": frame("B_05.01", {"c0010": "FR1", "c0100": value})}
    assert codes(tables) == []


def test_text_columns_are_not_checked() -> None:
    tables = {"B_05.01": frame("B_05.01", {"c0010": "FR1", "c0030": "ACME 12d-4"})}
    assert codes(tables) == []


def test_finding_lists_the_rows() -> None:
    tables = {
        "B_05.01": frame(
            "B_05.01", {"c0010": "FR1", "c0100": "10"}, {"c0010": "FR2", "c0100": "20d-3"}
        )
    }
    (message,) = [m for m in run_all(tables) if m.code == "DAT-015"]
    assert message.details == "#2 · '20d-3'"
    assert message.params["count"] == 1
