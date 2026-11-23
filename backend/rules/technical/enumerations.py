# SPDX-License-Identifier: EUPL-1.2
"""DAT-033: value outside the closed list of its field (Sprint 3, lot 6; #133, P3, P4).

The 41 fields with a closed list and their codes come from the EBA taxonomy 4.0
(``reference/dora/enumerations-4.0.json``; provenance in ``enumerations-4.0.provenance.json``).
A non-empty value must be one of the codes, exactly. Empty values are left to the rules on
mandatory fields. When the value is a code written in another case, or the label of a code,
the code to use is shown.
"""

from contracts import data_model
from contracts.dataset import RoIDataset
from contracts.messages import ValidationMessage
from rules.technical.identifiers import _finding
from rules.technical.locations import Hit

ROW_COLUMN = "_row"
CLOSED_LIST_CODE = "DAT-033"


def _suggestion(value: str, closed: data_model.ClosedList) -> str | None:
    folded = value.casefold()
    for code in sorted(closed.codes):
        if code.casefold() == folded or (closed.labels.get(code) or "").casefold() == folded:
            return code
    return None


class ClosedListRule:
    id = CLOSED_LIST_CODE

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        found: dict[tuple[str, str], list[Hit]] = {}
        lists: dict[tuple[str, str], str] = {}
        for (table, column), closed in data_model.closed_lists().items():
            frame = dataset.tables.get(table)
            if frame is None or column not in frame.columns:
                continue
            for row, raw in zip(frame[ROW_COLUMN], frame[column], strict=True):
                value = "" if raw is None else str(raw)
                if not value.strip() or value in closed.codes:
                    continue
                suggestion = _suggestion(value.strip(), closed)
                text = f"#{row} · {value!r}" + (f" → {suggestion}" if suggestion else "")
                found.setdefault((table, column), []).append(Hit(row, value, text))
                lists[(table, column)] = closed.id
        return [
            message
            for place, rows in sorted(found.items())
            for message in _finding(
                CLOSED_LIST_CODE, {place: rows}, labelled=True, list=lists[place]
            )
        ]
