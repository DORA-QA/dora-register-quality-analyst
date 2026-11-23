# SPDX-License-Identifier: EUPL-1.2
"""LEI (ISO 17442) and EUID checks on the identifier columns.

Which columns hold which identifier comes from
``reference/dora/identifier-fields-4.0.json``: some columns are always a LEI,
others are typed by a neighbouring column ("type of code"). An empty value is not
judged here (that is the mandatory-field check). Values are never corrected.
"""

import polars as pl

from contracts import data_model, identifiers
from contracts.dataset import RoIDataset
from contracts.messages import ValidationMessage, field_label, make_message
from contracts.naming import field_reference
from contracts.tables import column_values
from rules.technical.locations import Hit, describe, hit, located

ROW_COLUMN = "_row"

# LEI problem -> finding code
LEI_CODES = {
    identifiers.LEI_LENGTH_WRONG: "DAT-006",
    identifiers.LEI_BAD_CHARACTERS: "DAT-007",
    identifiers.LEI_BAD_MASK: "DAT-008",
    identifiers.LEI_BAD_CHECKSUM: "DAT-010",
}
WHITESPACE_CODE = "DAT-009"
EUID_SYNTAX_CODE = "DAT-011"
EUID_COUNTRY_CODE = "DAT-012"
EUID_MISMATCH_CODE = "DAT-013"
# EUID without a separator: the register identifier cannot be told apart (PO-24, #94).
EUID_NO_SEPARATOR_CODE = "DAT-031"

# (table, EUID columns, column holding the country of the same entity), value 'eba_GA:FR'.
EUID_ENTITY_COUNTRY = (("B_05.01", ("c0010", "c0030"), "c0080"),)


def _cells(frame: pl.DataFrame, column: str, type_column: str | None):
    """(row, value, type) for each non-empty value of a column (columns read once, as lists)."""
    present = frame.columns
    if column not in present:
        return
    numbers = column_values(frame, ROW_COLUMN)
    types = column_values(frame, type_column) if type_column and type_column in present else None
    for index, value in enumerate(column_values(frame, column)):
        if value is None or value == "":
            continue
        yield numbers[index], str(value), (types[index] if types is not None else None)


def _identifier_cells(dataset: RoIDataset, kind: str):
    """Every (table, column, row, value) declared as ``kind`` ('LEI' or 'EUID')."""
    fields = data_model.identifier_fields()
    if kind == "LEI":
        for table, column in fields.lei_columns:
            if table in dataset.tables:
                for row, value, _ in _cells(dataset.tables[table], column, None):
                    yield table, column, row, value
    member = fields.lei_member if kind == "LEI" else fields.euid_member
    for table, column, type_column in fields.typed:
        if table in dataset.tables:
            for row, value, declared in _cells(dataset.tables[table], column, type_column):
                # A value that clearly belongs to another type is reported once, by DAT-014.
                if declared == member and not identifiers.looks_like_other_kind(
                    value, identifiers.TYPE_KINDS.get(declared)
                ):
                    yield table, column, row, value


def _finding(
    code: str, lines: dict[tuple[str, str], list[Hit]], labelled: bool = False, **params: object
):
    """One finding per table and column, so the reader can fix one column at a time.

    ``labelled``: the column is written with its official ITS label (PO, #179).
    """
    return [
        located(
            make_message(
                code,
                details=describe([h.text for h in rows]),
                table=table,
                column=field_label(field_reference(table, column))
                if labelled
                else field_reference(table, column),
                count=len(rows),
                **params,
            ),
            table,
            column,
            rows,
        )
        for (table, column), rows in sorted(lines.items())
    ]


class LeiRule:
    id = "LEI"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        by_code: dict[str, dict[tuple[str, str], list[Hit]]] = {}
        spaces: dict[tuple[str, str], list[Hit]] = {}
        space_kinds: dict[tuple[str, str], list[int]] = {}
        for table, column, row, value in _identifier_cells(dataset, "LEI"):
            analysis = identifiers.analyse_lei(value)
            place = (table, column)
            if analysis.has_whitespace:
                spaces.setdefault(place, []).append(hit(row, value))
                counts = space_kinds.setdefault(place, [0, 0, 0])
                counts[0] += analysis.leading_spaces
                counts[1] += analysis.trailing_spaces
                counts[2] += analysis.inner_spaces
            if analysis.problem != identifiers.LEI_OK:
                code = LEI_CODES[analysis.problem]
                by_code.setdefault(code, {}).setdefault(place, []).append(hit(row, value))

        messages: list[ValidationMessage] = []
        for code in ("DAT-006", "DAT-007", "DAT-008", "DAT-010"):
            messages += _finding(code, by_code.get(code, {}))
        for (table, column), rows in sorted(spaces.items()):
            leading, trailing, inner = space_kinds[(table, column)]
            message = make_message(
                WHITESPACE_CODE,
                details=describe([h.text for h in rows]),
                table=table,
                column=field_reference(table, column),
                count=len(rows),
                leading=leading,
                trailing=trailing,
                inner=inner,
            )
            messages.append(located(message, table, column, rows))
        return messages


class EuidRule:
    id = "EUID"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        eea = data_model.eea_countries()
        syntax: dict[tuple[str, str], list[Hit]] = {}
        country: dict[tuple[str, str], list[Hit]] = {}
        undotted: dict[tuple[str, str], list[Hit]] = {}
        for table, column, row, value in _identifier_cells(dataset, "EUID"):
            analysis = identifiers.analyse_euid(value)
            place = (table, column)
            if analysis.problem != identifiers.EUID_OK:
                syntax.setdefault(place, []).append(hit(row, value))
                continue
            if analysis.country not in eea:
                country.setdefault(place, []).append(hit(row, value))
            if not identifiers.has_registry_separator(value):
                undotted.setdefault(place, []).append(hit(row, value))
        return (
            _finding(EUID_SYNTAX_CODE, syntax)
            + _finding(EUID_COUNTRY_CODE, country)
            + self._mismatches(dataset)
            + _finding(EUID_NO_SEPARATOR_CODE, undotted)
        )

    @staticmethod
    def _mismatches(dataset: RoIDataset) -> list[ValidationMessage]:
        """EUID prefix against the country declared on the same row (headquarters)."""
        euid = data_model.identifier_fields().euid_member
        found: dict[tuple[str, str], list[Hit]] = {}
        for table, columns, country_column in EUID_ENTITY_COUNTRY:
            frame = dataset.tables.get(table)
            if frame is None or country_column not in frame.columns:
                continue
            for code_column in columns:
                type_column = next(
                    (
                        t
                        for tb, c, t in data_model.identifier_fields().typed
                        if tb == table and c == code_column
                    ),
                    None,
                )
                if code_column not in frame.columns or type_column not in frame.columns:
                    continue
                for row, value, declared in _cells(frame, code_column, type_column):
                    if declared != euid or identifiers.looks_like_other_kind(
                        value, identifiers.KIND_EUID
                    ):
                        continue
                    analysis = identifiers.analyse_euid(value)
                    declared_country = str(frame[country_column][row - 1] or "")
                    country = declared_country.rsplit(":", 1)[-1]
                    if (
                        analysis.country
                        and country
                        and not identifiers.same_country(analysis.country, country)
                    ):
                        found.setdefault((table, code_column), []).append(
                            hit(row, value, f" ≠ {country}")
                        )
        return _finding(EUID_MISMATCH_CODE, found)
