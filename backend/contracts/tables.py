# SPDX-License-Identifier: EUPL-1.2
"""Reading the tables of a dataset: rows as dictionaries, columns read once (brief §17.5).

Shared by the rules and the indicators, which depend on ``contracts`` only. Values are read as
reported; an empty text is read as ``None``. Callers must not modify what they receive.
"""

import weakref
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

import polars as pl

from contracts.dataset import RoIDataset
from contracts.json_types import Row

ROW_COLUMN = "_row"

# Columns a rule asked for that the table does not have (red team RT-09): while a rule runs, the
# engine collects them, so that its check reads "not evaluated" instead of "passed".
_MISSING_READS: ContextVar[set[tuple[str, str]] | None] = ContextVar("missing_reads", default=None)


@contextmanager
def recording_missing_columns() -> Iterator[set[tuple[str, str]]]:
    """Collect the (table, column) pairs read by the code inside but absent from their table."""
    found: set[tuple[str, str]] = set()
    token = _MISSING_READS.set(found)
    try:
        yield found
    finally:
        _MISSING_READS.reset(token)


# A cell is a text, a number, a date or None, as Polars returns it.
Cell = object
_COLUMNS: dict[int, tuple[weakref.ref[pl.DataFrame], dict[str, list[Cell]]]] = {}


def column_values(frame: pl.DataFrame, column: str) -> list[Cell]:
    """Values of a column as a list, kept while the frame lives (several rules read it).

    Callers must not modify the list.
    """
    entry = _COLUMNS.get(id(frame))
    if entry is None or entry[0]() is not frame:
        key = id(frame)

        def forget(_ref: weakref.ref[pl.DataFrame], key: int = key) -> None:
            _COLUMNS.pop(key, None)

        entry = (weakref.ref(frame, forget), {})
        _COLUMNS[key] = entry
    cache = entry[1]
    if column not in cache:
        cache[column] = _shared(frame[column].to_list())
    return cache[column]


def _shared(values: list[Cell]) -> list[Cell]:
    """One object per distinct value: codes, types and dates repeat on most rows.

    A list built by Polars holds one text object per cell; sharing equal values divides the
    memory of a large register by about three (load test of 30/10, 3.5 million rows).
    """
    seen: dict[Cell, Cell] = {}
    return [seen.setdefault(value, value) for value in values]


def clear_column_cache() -> None:
    """Forget the columns read: they serve during the analysis only (load test of 30/10).

    The register itself stays in its dataset for the time allowed; these lists were holding
    about 1.4 GB more for 3.5 million rows.
    """
    _COLUMNS.clear()


def rows(dataset: RoIDataset, table: str, *columns: str) -> Iterator[Row]:
    """Rows of a table with the requested columns (absent column read as empty).

    Nothing is yielded when the table is absent: a rule then has nothing to compare.
    """
    frame = dataset.tables.get(table)
    if frame is None or frame.height == 0:
        return
    # Whole columns as lists, read once per frame: much faster than iterating rows (brief §17.5).
    recorder = _MISSING_READS.get()
    if recorder is not None:
        recorder.update((table, c) for c in columns if c not in frame.columns)
    numbers = column_values(frame, ROW_COLUMN)
    values = {c: column_values(frame, c) if c in frame.columns else None for c in columns}
    for index, number in enumerate(numbers):
        record: Row = {ROW_COLUMN: number}
        for column, cells in values.items():
            record[column] = None if cells is None else _clean(cells[index])
        yield record


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text != "" else None


def by_code(dataset: RoIDataset, table: str, key: str, *columns: str) -> dict[str, Row]:
    """First row of each code of a reference table (duplicates are DAT-004's business)."""
    found: dict[str, Row] = {}
    for row in rows(dataset, table, key, *columns):
        code = row[key]
        if code is not None:
            found.setdefault(str(code), row)
    return found
