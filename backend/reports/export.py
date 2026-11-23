# SPDX-License-Identifier: EUPL-1.2
"""Export of the findings of an analysis, as CSV or JSON Lines (Sprint 4, lot 3, MUST).

Brief of the Sprint 4, §15 and §16; note of 02/11/2026, §2.6:

- one line per occurrence (a finding without occurrence gives one line without place), with the
  22 fields of ``FIELDS``, headers in English and the engine version on every line;
- generated as a stream, line by line: nothing is written to disk nor kept after sending, and
  no value goes to the logs;
- CSV for spreadsheets: UTF-8 with a byte order mark, semicolons; a cell that starts with
  ``=``, ``+``, ``-``, ``@``, a tab or a carriage return is prefixed with ``'`` so that a
  spreadsheet does not run it as a formula;
- texts in the language asked; values from the register included unless the user excludes them;
- the disclaimer of DORA QA closes every export: after an empty line, as a one-cell line in the
  CSV; as a last object ``{"record_type": "disclaimer", "text": ...}`` in JSON Lines. Notes on
  the analysis (GLEIF checks absent from the offline version) come just before it, the same way,
  with ``"record_type": "notice"``.
"""

import csv
import io
import json
from collections.abc import Callable, Iterable, Iterator

from contracts.check_report import category_of_code, check_of_code, origin_of_code
from contracts.disclaimer import disclaimer
from contracts.messages import Occurrence, ValidationMessage, render_message

FIELDS = (
    "engine_version",
    "import_id",
    "finding_index",
    "code",
    "check_id",
    "origin",
    "severity_status",
    "profile",
    "severity",
    "category",
    "message",
    "explanation",
    "recommendation",
    "expert_advice",
    "reference",
    "authority_codes",
    "source_table",
    "source_row",
    "source_column",
    "source_value",
    "target_table",
    "target_column",
)
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")

Row = dict[str, str | int | None]


def _matches(
    occurrence: Occurrence, table: str | None, row: int | None, column: str | None
) -> bool:
    return (
        (table is None or occurrence.table == table)
        and (row is None or occurrence.row == row)
        and (column is None or occurrence.column == column)
    )


def rows(
    messages: list[ValidationMessage],
    *,
    import_id: str,
    engine_version: str,
    language: str,
    indices: set[int] | None = None,
    table: str | None = None,
    row: int | None = None,
    column: str | None = None,
    include_values: bool = True,
    profile_of: Callable[[str], str | None] = lambda code: None,
) -> Iterator[Row]:
    """The lines of the export, finding by finding, in the order of the answer.

    ``indices``: positions of the findings to export (the filters of the screen); all if None.
    ``table``, ``row``, ``column``: only the occurrences at that place (then a finding without
    a matching occurrence is left out).
    ``profile_of``: profile of a code (REGULATORY, EXPERT), given by the caller, since the
    profiles belong to ``scoring``.
    """
    place_filter = table is not None or row is not None or column is not None
    for index, message in enumerate(messages):
        if indices is not None and index not in indices:
            continue
        occurrences = [o for o in message.occurrences if _matches(o, table, row, column)]
        if place_filter and not occurrences:
            continue
        rendered = render_message(message, language)
        common: Row = {
            "engine_version": engine_version,
            "import_id": import_id,
            "finding_index": index,
            "code": message.code,
            "check_id": check_of_code(message.code),
            "origin": origin_of_code(message.code),
            "severity_status": rendered.severity_status,
            "profile": profile_of(message.code),
            "severity": message.severity.value,
            "category": category_of_code(message.code),
            "message": rendered.message,
            "explanation": rendered.explanation,
            "recommendation": rendered.recommendation,
            "expert_advice": rendered.expert_advice,
            "reference": rendered.reference.text if rendered.reference else None,
            "authority_codes": " ".join(message.official_codes) or None,
        }
        places: list[Occurrence | None] = list(occurrences) or [None]
        for occurrence in places:
            line = dict(common)
            line.update(
                {
                    "source_table": occurrence.table if occurrence else None,
                    "source_row": occurrence.row if occurrence else None,
                    "source_column": occurrence.column if occurrence else None,
                    "source_value": occurrence.value if occurrence and include_values else None,
                    "target_table": occurrence.target_table if occurrence else None,
                    "target_column": occurrence.target_column if occurrence else None,
                }
            )
            yield line


def neutralise(value: str | int | None) -> str:
    """A cell as text, with formulas made harmless for spreadsheets."""
    if value is None:
        return ""
    text = str(value)
    return f"'{text}" if text.startswith(FORMULA_STARTS) else text


def csv_stream(
    lines: Iterable[Row], language: str = "en", notes: Iterable[str] = ()
) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")

    def flush() -> str:
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return text

    writer.writerow(FIELDS)
    yield "﻿" + flush()
    for line in lines:
        writer.writerow([neutralise(line[name]) for name in FIELDS])
        yield flush()
    writer.writerow([])
    for note in notes:
        writer.writerow([note])
    writer.writerow([disclaimer(language)])
    yield flush()


def jsonl_stream(
    lines: Iterable[Row], language: str = "en", notes: Iterable[str] = ()
) -> Iterator[str]:
    for line in lines:
        yield json.dumps({name: line[name] for name in FIELDS}, ensure_ascii=False) + "\n"
    for note in notes:
        yield json.dumps({"record_type": "notice", "text": note}, ensure_ascii=False) + "\n"
    closing = {"record_type": "disclaimer", "text": disclaimer(language)}
    yield json.dumps(closing, ensure_ascii=False) + "\n"
