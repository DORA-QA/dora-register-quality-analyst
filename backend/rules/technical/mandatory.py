# SPDX-License-Identifier: EUPL-1.2
"""Mandatory fields that no active EBA rule checks (PO-32, #121).

The taxonomy declares 41 mandatory fields through 9 existence rules, all inactive in the EBA list
(PO-1). The active conditional rules (DAT-023) cover most of them; the fields left over are
checked here, on every row: a non-nullable field of the EBA data model must not be empty (the
ACPR rejects such a value with a v888*_m code, the ESAs do not reject it). Primary key columns
are left to DAT-003. The list is computed from the reference files, so it follows any change of
the EBA rules without touching the code.
"""

from functools import lru_cache

from contracts import data_model
from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from contracts.naming import field_reference
from rules.technical.locations import describe

ROW_COLUMN = "_row"
MANDATORY_CODE = "DAT-032"


@lru_cache
def uncovered_mandatory_fields() -> tuple[tuple[str, str], ...]:
    """Mandatory fields that are neither a primary key nor the target of an active rule."""
    # Imported here: rules.eba_conditional itself imports from rules.technical.
    from rules.eba_conditional import compiled_rules

    targets = {(rule.table, rule.target) for rule in compiled_rules() if hasattr(rule, "target")}
    keys = {
        (code, column)
        for code, model in data_model.tables().items()
        for column in model.primary_key
    }
    return tuple(
        sorted(f for f in data_model.mandatory_fields() if f not in targets and f not in keys)
    )


class UncoveredMandatoryFieldRule:
    id = "MANDATORY_FIELD"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        for table, column in uncovered_mandatory_fields():
            frame = dataset.tables.get(table)
            # A column missing from the header is DAT-030's finding, not this one.
            if frame is None or column not in frame.columns:
                continue
            hits = [
                (row, value)
                for row, value in zip(frame[ROW_COLUMN], frame[column], strict=True)
                if value is None or not str(value).strip()
            ]
            if not hits:
                continue
            reference = field_reference(table, column)
            message = make_message(
                MANDATORY_CODE,
                details=describe([f"#{row} · {reference}" for row, _ in hits]),
                table=table,
                column=reference,
                count=len(hits),
            )
            occurrences = [
                Occurrence(table=table, row=row, column=column, value=value) for row, value in hits
            ]
            messages.append(with_occurrences(message, occurrences, total=len(hits)))
        return messages
