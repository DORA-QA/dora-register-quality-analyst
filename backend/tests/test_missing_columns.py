# SPDX-License-Identifier: EUPL-1.2
"""Toute colonne du schéma doit figurer dans l'en-tête : DAT-030, bloquant (PO-26, issue #96)."""

from contracts import data_model
from tests.test_technical_rules import frame, run_all


def found(table: str, *rows: dict[str, str], drop: str | None = None):
    data = frame(table, *rows)
    if drop:
        data = data.drop(drop)
    return [m for m in run_all({table: data}) if m.code == "DAT-030"]


def test_a_complete_header_is_accepted() -> None:
    columns = data_model.tables()["B_01.01"].columns
    assert found("B_01.01", {c: "x" for c in columns}) == []


def test_a_missing_optional_column_is_blocking() -> None:
    columns = data_model.tables()["B_01.01"].columns
    messages = found("B_01.01", {c: "x" for c in columns}, drop="c0020")

    assert len(messages) == 1
    assert messages[0].severity.name == "BLOCKER"
    assert messages[0].params["count"] == 1
    assert "B_01.01.0020" in messages[0].details
