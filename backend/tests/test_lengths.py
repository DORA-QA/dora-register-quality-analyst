# SPDX-License-Identifier: EUPL-1.2
"""Maximum length of free-text values (DAT-022)."""

from contracts import data_model
from tests.test_technical_rules import frame, run_all


def details(tables) -> list[str]:
    return [m.details for m in run_all(tables) if m.code == "DAT-022"]


def test_reference_covers_the_text_columns() -> None:
    limits = data_model.max_lengths()
    assert len(limits) == 31
    assert set(limits.values()) == {255}
    assert ("B_05.01", "c0050") in limits
    assert ("B_01.02", "c0010") not in limits  # LEI: left to the LEI checks
    assert ("B_05.01", "c0080") not in limits  # country: a coded value


def test_length_is_counted_in_characters() -> None:
    accented = "é" * 255  # 510 bytes in UTF-8, 255 characters
    tables = {"B_05.01": frame("B_05.01", {"c0010": "1", "c0050": accented})}
    assert details(tables) == []


def test_too_long_value_is_reported_once_per_column() -> None:
    rows = [{"c0010": "1", "c0050": "x" * 256}, {"c0010": "2", "c0050": "y" * 300}]
    tables = {"B_05.01": frame("B_05.01", *rows)}
    (message,) = [m for m in run_all(tables) if m.code == "DAT-022"]
    assert message.details == "#1 · 256 > 255\n#2 · 300 > 255"
    assert message.params["limit"] == 255
    assert message.params["count"] == 2


def test_supplementary_plane_characters_count_as_one() -> None:
    emoji = "😀" * 255
    tables = {"B_05.01": frame("B_05.01", {"c0010": "1", "c0050": emoji})}
    assert details(tables) == []
