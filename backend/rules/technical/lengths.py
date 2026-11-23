# SPDX-License-Identifier: EUPL-1.2
"""Maximum length of free-text values (EBA data model, version of 1 April 2025).

Length is counted in Unicode characters (code points), never in bytes, so that accented
letters count as one. Values are never cut.
"""

from contracts import data_model
from contracts.dataset import RoIDataset
from contracts.messages import ValidationMessage
from rules.technical.identifiers import _finding
from rules.technical.locations import Hit

ROW_COLUMN = "_row"
LENGTH_CODE = "DAT-022"


class MaxLengthRule:
    id = "MAX_LENGTH"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        found: dict[tuple[str, str], list[Hit]] = {}
        limits: dict[tuple[str, str], int] = {}
        for (table, column), limit in data_model.max_lengths().items():
            frame = dataset.tables.get(table)
            if frame is None or column not in frame.columns:
                continue
            for row, value in zip(frame[ROW_COLUMN], frame[column], strict=True):
                if value is not None and len(str(value)) > limit:
                    found.setdefault((table, column), []).append(
                        Hit(row, str(value), f"#{row} · {len(str(value))} > {limit}")
                    )
                    limits[(table, column)] = limit
        return [
            message
            for (place, rows) in sorted(found.items())
            for message in _finding(LENGTH_CODE, {place: rows}, limit=limits[place])
        ]
