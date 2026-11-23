# SPDX-License-Identifier: EUPL-1.2
"""Decimals suffix in numeric cells (xBRL-CSV).

The EBA forbids the "decimals suffix" feature (a value such as ``78920030d-4`` in a
monetary cell): the precision is declared once, in ``parameters.csv``. The check
only looks for the forbidden form; it does not interpret the suffix.
"""

import re

from contracts import data_model
from contracts.dataset import RoIDataset
from contracts.messages import ValidationMessage, field_label, make_message
from contracts.naming import field_reference
from rules.technical.locations import describe, hit, located

ROW_COLUMN = "_row"
SUFFIX_CODE = "DAT-015"
# A digit followed by "d" and an integer, at the end of the value.
DECIMALS_SUFFIX = re.compile(r"\d[dD][+-]?\d+$")


class NumericSuffixRule:
    id = "NUMERIC_SUFFIX"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        for table, column in data_model.numeric_columns():
            frame = dataset.tables.get(table)
            if frame is None or column not in frame.columns:
                continue
            rows = [
                hit(row, value)
                for row, value in zip(frame[ROW_COLUMN], frame[column], strict=True)
                if value and DECIMALS_SUFFIX.search(str(value).strip())
            ]
            if rows:
                message = make_message(
                    SUFFIX_CODE,
                    details=describe([h.text for h in rows]),
                    table=table,
                    column=field_label(field_reference(table, column)),
                    count=len(rows),
                )
                messages.append(located(message, table, column, rows))
        return messages
