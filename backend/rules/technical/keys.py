# SPDX-License-Identifier: EUPL-1.2
"""EBA 805, 806, 807: primary keys and foreign keys.

An empty value is a missing value. Keys are compared exactly as reported (no
trimming, no case change): a difference of spaces or case is a difference of key
for the authority too.
"""

import polars as pl

from contracts import data_model
from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from rules.technical.headers import reference_list
from rules.technical.locations import describe

ROW_COLUMN = "_row"


def _text(frame: pl.DataFrame, column: str) -> pl.Series:
    """Values of a column as text, empty strings read as missing. Absent column: all missing."""
    if column not in frame.columns:
        return pl.Series([None] * frame.height, dtype=pl.Utf8)
    return frame[column].cast(pl.Utf8).replace("", None)


def _key_frame(frame: pl.DataFrame, columns: tuple[str, ...]) -> pl.DataFrame:
    data = {name: _text(frame, name) for name in columns}
    data[ROW_COLUMN] = frame[ROW_COLUMN]
    return pl.DataFrame(data)


class MissingKeyRule:
    id = "DAT-003"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        messages = []
        for code, model in sorted(data_model.tables().items()):
            frame = dataset.tables.get(code)
            if frame is None or frame.height == 0 or not model.primary_key:
                continue
            keys = _key_frame(frame, model.primary_key)
            optional = data_model.optional_key_columns(code)
            lines = []
            places: list[Occurrence] = []
            for row in keys.iter_rows(named=True):
                missing = [c for c in model.primary_key if row[c] is None and c not in optional]
                if missing:
                    lines.append(f"#{row[ROW_COLUMN]} · {reference_list(code, tuple(missing))}")
                    places += [
                        Occurrence(table=code, row=row[ROW_COLUMN], column=c) for c in missing
                    ]
            if lines:
                message = make_message(
                    "DAT-003",
                    details=describe(lines),
                    table=code,
                    count=len(lines),
                    columns=reference_list(code, model.primary_key),
                )
                messages.append(with_occurrences(message, places))
        return messages


class DuplicateKeyRule:
    id = "DAT-004"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        messages = []
        for code, model in sorted(data_model.tables().items()):
            frame = dataset.tables.get(code)
            if frame is None or frame.height == 0 or not model.primary_key:
                continue
            optional = data_model.optional_key_columns(code)
            required = [c for c in model.primary_key if c not in optional]
            keys = _key_frame(frame, model.primary_key).drop_nulls(subset=required)
            # An empty optional key column (allowed) is part of the key, as an empty value.
            keys = keys.with_columns([pl.col(c).fill_null("") for c in optional])
            repeated = keys.filter(keys.select(model.primary_key).is_duplicated()).sort(ROW_COLUMN)
            seen: set[tuple] = set()
            lines = []
            places: list[Occurrence] = []
            for row in repeated.iter_rows(named=True):
                key = tuple(row[c] for c in model.primary_key)
                if key in seen:
                    lines.append(f"#{row[ROW_COLUMN]} · {' | '.join(key)}")
                    places += [
                        Occurrence(table=code, row=row[ROW_COLUMN], column=c, value=row[c] or None)
                        for c in model.primary_key
                    ]
                seen.add(key)
            if lines:
                message = make_message(
                    "DAT-004",
                    details=describe(lines),
                    table=code,
                    count=len(lines),
                    columns=reference_list(code, model.primary_key),
                )
                messages.append(with_occurrences(message, places))
        return messages


class ForeignKeyRule:
    id = "DAT-005"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        messages = []
        for constraint in data_model.key_constraints():
            source = dataset.tables.get(constraint.source_table)
            target = dataset.tables.get(constraint.target_table)
            # A table that did not load is reported by the import steps, not here.
            if source is None or target is None or source.height == 0:
                continue
            referenced = _key_frame(source, constraint.source_columns)
            # Empty source values are not references: whether they are allowed is a
            # question of mandatory fields, not of keys.
            referenced = referenced.drop_nulls(subset=list(constraint.source_columns))
            available = (
                _key_frame(target, constraint.target_columns)
                .drop_nulls(subset=list(constraint.target_columns))
                .select(constraint.target_columns)
                .unique()
            )
            available = available.rename(
                dict(zip(constraint.target_columns, constraint.source_columns, strict=True))
            )
            orphans = referenced.join(available, on=list(constraint.source_columns), how="anti")
            ordered = list(orphans.sort(ROW_COLUMN).iter_rows(named=True))
            lines = [
                f"#{row[ROW_COLUMN]} · "
                + " | ".join(str(row[c]) for c in constraint.source_columns)
                for row in ordered
            ]
            places = [
                Occurrence(
                    table=constraint.source_table, row=row[ROW_COLUMN], column=c, value=row[c]
                )
                for row in ordered
                for c in constraint.source_columns
            ]
            if lines:
                message = make_message(
                    "DAT-005",
                    details=describe(lines),
                    table=constraint.source_table,
                    count=len(lines),
                    columns=reference_list(constraint.source_table, constraint.source_columns),
                    target=reference_list(constraint.target_table, constraint.target_columns),
                    constraint=constraint.id,
                )
                messages.append(with_occurrences(message, places))
        return messages


class ConditionalKeyRule:
    """A key column mandatory only in some cases (B_04.01.0040 for a branch).

    Branch without a code: DAT-027. Not a branch: the EBA expects the text "Not Applicable"
    (Q&A 2024_7282, FAQ 64), an empty value is accepted by the ACPR, so only DAT-028 (MINOR).
    """

    id = "DAT-027"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        messages = []
        for (table, column), (condition, value) in sorted(
            data_model.CONDITIONAL_KEY_COLUMNS.items()
        ):
            frame = dataset.tables.get(table)
            if frame is None or frame.height == 0 or condition not in frame.columns:
                continue
            missing: list[str] = []
            empty: list[str] = []
            places: dict[str, list[Occurrence]] = {"DAT-027": [], "DAT-028": []}
            for row, key, state in zip(
                frame[ROW_COLUMN], _text(frame, column), _text(frame, condition), strict=True
            ):
                if state == value and (key is None or data_model.is_not_applicable(key)):
                    missing.append(f"#{row}" if key is None else f"#{row} · {key!r}")
                    places["DAT-027"].append(
                        Occurrence(table=table, row=row, column=column, value=key)
                    )
                elif state is not None and state != value and key is None:
                    empty.append(f"#{row}")
                    places["DAT-028"].append(Occurrence(table=table, row=row, column=column))
            params = {
                "table": table,
                "column": reference_list(table, (column,)),
                "condition": reference_list(table, (condition,)),
            }
            for code, lines in (("DAT-027", missing), ("DAT-028", empty)):
                if lines:
                    message = make_message(
                        code, details=describe(lines), count=len(lines), **params
                    )
                    messages.append(with_occurrences(message, places[code]))
        return messages


FRAMEWORK_TABLE, FRAMEWORK_TYPE, FRAMEWORK_REF = "B_02.01", "c0020", "c0030"
FRAMEWORK_VALUE = "eba_CO:x2"


class FrameworkContractTypeRule:
    """B_02.01.0030 must cite a contract whose type (B_02.01.0020) is eba_CO:x2 (framework).

    PO decision, issue #76: blocking. A reference to a contract that does not exist is the
    foreign key DAT-005 (R13), not reported again here.
    """

    id = "DAT-029"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        frame = dataset.tables.get(FRAMEWORK_TABLE)
        if frame is None or frame.height == 0 or FRAMEWORK_REF not in frame.columns:
            return []
        types = dict(zip(_text(frame, "c0010"), _text(frame, FRAMEWORK_TYPE), strict=True))
        lines = []
        places: list[Occurrence] = []
        for row, reference in zip(frame[ROW_COLUMN], _text(frame, FRAMEWORK_REF), strict=True):
            if reference is None or reference not in types:
                continue
            found = types[reference]
            if found != FRAMEWORK_VALUE:
                lines.append(f"#{row} · {reference!r} ({found or '∅'})")
                places.append(
                    Occurrence(
                        table=FRAMEWORK_TABLE, row=row, column=FRAMEWORK_REF, value=reference
                    )
                )
        if not lines:
            return []
        message = make_message(
            "DAT-029",
            details=describe(lines),
            table=FRAMEWORK_TABLE,
            count=len(lines),
            column=reference_list(FRAMEWORK_TABLE, (FRAMEWORK_REF,)),
            type_column=reference_list(FRAMEWORK_TABLE, (FRAMEWORK_TYPE,)),
            expected=FRAMEWORK_VALUE,
        )
        return [with_occurrences(message, places)]
