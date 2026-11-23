# SPDX-License-Identifier: EUPL-1.2
"""Contrat des constats croisés (brief du Sprint 3, §14.1 et §14.2) : évolution compatible."""

from contracts.api_models import MessageModel
from contracts.messages import Occurrence, make_message, render_message, with_occurrences

PARAMS = {
    "table": "B_02.02",
    "count": 1,
    "columns": "c0030",
    "target": "B_05.01",
    "constraint": "R1",
}


def test_an_occurrence_carries_the_expected_target_and_its_side():
    message = with_occurrences(
        make_message("DAT-005", **PARAMS),
        [
            Occurrence(
                table="B_01.02",
                row=3,
                column="c0030",
                value="FR",
                target_table="B_05.01",
                target_column="c0080",
                side="source",
            ),
            Occurrence(table="B_05.01", row=7, column="c0080", value="DE", side="target"),
        ],
    )
    model = MessageModel.from_rendered(render_message(message, "fr"), origin="PO_VALIDATED")
    first, second = model.occurrences
    assert (first.target_table, first.target_column, first.side) == ("B_05.01", "c0080", "source")
    assert (second.table, second.value, second.side) == ("B_05.01", "DE", "target")
    assert model.origin == "PO_VALIDATED"


def test_single_table_occurrences_are_unchanged():
    message = with_occurrences(
        make_message("DAT-005", **PARAMS), [Occurrence(table="B_02.02", row=1)]
    )
    dumped = MessageModel.from_rendered(render_message(message)).model_dump()
    occurrence = dumped["occurrences"][0]
    assert occurrence["target_table"] is None and occurrence["side"] is None
    assert {"table", "row", "column", "value"} <= occurrence.keys()
