# SPDX-License-Identifier: EUPL-1.2
"""Naming conventions of the project, used everywhere.

- A table is identified by its official template code: ``B_01.01``.
- A column is identified by its CSV code: ``c0010``.
- The reference shown to users follows the EBA style: ``B_01.01.0010``.
  (The regulation numbers fields ``RT.01.01.0010``; the EBA/CSV number is used
  everywhere in the product, the regulation number only as a complement.)
"""

import re

TABLE_FILE_PATTERN = re.compile(r"^b_(\d{2})\.(\d{2})\.csv$", re.IGNORECASE)
TABLE_CODE_PATTERN = re.compile(r"^B_(\d{2})\.(\d{2})$")
COLUMN_CODE_PATTERN = re.compile(r"^c(\d{4})$")


def table_code_from_file(file_name: str) -> str | None:
    """Return the table code of a CSV file name (``b_01.01.csv`` -> ``B_01.01``)."""
    match = TABLE_FILE_PATTERN.match(file_name)
    return f"B_{match.group(1)}.{match.group(2)}" if match else None


def file_name_from_table_code(table_code: str) -> str:
    """Return the expected CSV file name of a table (``B_01.01`` -> ``b_01.01.csv``)."""
    return f"{table_code.lower()}.csv"


def field_reference(table_code: str, column_code: str | None = None) -> str:
    """Return the reference shown to users, in the EBA style.

    ``B_06.01`` + ``c0050`` -> ``B_06.01.0050``. The table alone is returned
    unchanged, and so is any unknown format (never guessed).
    """
    if not TABLE_CODE_PATTERN.match(table_code):
        return table_code
    column = COLUMN_CODE_PATTERN.match(column_code or "")
    return f"{table_code}.{column.group(1)}" if column else table_code
