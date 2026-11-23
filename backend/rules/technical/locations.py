# SPDX-License-Identifier: EUPL-1.2
"""Writes where a finding is, without any language.

Each line is ``#<data row> · <reference> · <value>``. ``#12`` is the 12th data
row under the header, as in the EBA feedback. The list is capped so that one
finding stays readable. The same places are also attached as structured occurrences.
"""

from typing import NamedTuple

from contracts.messages import Occurrence, ValidationMessage, clip, with_occurrences

MAX_LINES = 25


class Hit(NamedTuple):
    """One place a finding was seen: data row, raw value and the line shown in ``details``."""

    row: int | None
    value: str | None
    text: str


def hit(row: int, value: object, suffix: str = "") -> Hit:
    """The usual line ``#row · 'value'``, with the raw value kept for the occurrence."""
    raw = None if value is None else str(value)
    shown = None if raw is None else clip(raw)
    return Hit(row, raw, f"#{row} · {shown!r}{suffix}")


def located(
    message: ValidationMessage, table: str, column: str | None, hits: list[Hit]
) -> ValidationMessage:
    """Attach the structured occurrences (table, row, column, value): brief, epic 9."""
    return with_occurrences(
        message,
        [Occurrence(table=table, row=h.row, column=column, value=h.value) for h in hits],
        total=len(hits),
    )


def describe(lines: list[str]) -> str | None:
    if not lines:
        return None
    shown = lines[:MAX_LINES]
    if len(lines) > MAX_LINES:
        shown.append(f"… (+{len(lines) - MAX_LINES})")
    return "\n".join(shown)
