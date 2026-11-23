# SPDX-License-Identifier: EUPL-1.2
"""EBA 801: the header of a table may only use column codes of the taxonomy."""

from contracts import data_model
from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from contracts.naming import field_reference
from rules.technical.locations import describe

ROW_COLUMN = "_row"


class UnknownColumnsRule:
    id = "DAT-001"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        model = data_model.tables()
        messages = []
        for code, frame in sorted(dataset.tables.items()):
            known = model.get(code)
            if known is None:
                continue
            unknown = [c for c in frame.columns if c != ROW_COLUMN and c not in known.columns]
            if unknown:
                message = make_message(
                    "DAT-001",
                    details=describe([f"{c}" for c in unknown]),
                    table=code,
                    count=len(unknown),
                )
                messages.append(_columns(message, code, unknown))
        return messages


class MissingColumnsRule:
    """Every column of the schema must be in the header, optional ones included (PO-26, #96).

    ACPR (27/08/2025, p. 6-7) and the Filing Rules v5.9 (p. 64, rule 2) reject a header with a
    column fewer; the EBA (April 2025, p. 26) would accept it. The product follows the ACPR.
    """

    id = "DAT-030"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        model = data_model.tables()
        messages = []
        for code, frame in sorted(dataset.tables.items()):
            known = model.get(code)
            if known is None:
                continue
            missing = [c for c in known.columns if c not in frame.columns]
            if missing:
                message = make_message(
                    "DAT-030",
                    details=describe([field_reference(code, c) for c in missing]),
                    table=code,
                    count=len(missing),
                )
                messages.append(_columns(message, code, missing))
        return messages


def _columns(message: ValidationMessage, table: str, columns: list[str]) -> ValidationMessage:
    """A header finding is located on columns, not on rows."""
    return with_occurrences(
        message, [Occurrence(table=table, column=c) for c in columns], total=len(columns)
    )


def reference_list(table: str, columns: tuple[str, ...]) -> str:
    return ", ".join(field_reference(table, column) for column in columns)
