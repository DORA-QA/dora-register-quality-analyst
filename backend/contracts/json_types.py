# SPDX-License-Identifier: EUPL-1.2
"""Untyped boundaries (mypy policy of the Sprint 4, decision A8 of the PO, 02/11/2026).

``Any`` is forbidden in the strictly checked modules, except here, for the two places where
the content is not typed:

- ``JsonDict``: a JSON file read from ``reference/``;
- ``Row``: a row of a table, as returned by ``contracts.tables.rows`` (the data row number
  under ``_row``, an integer, then the requested columns, texts or None).

Every module goes through these aliases, so that ``Any`` stays in one visible place.
"""

from typing import Any

JsonDict = dict[str, Any]
Row = dict[str, Any]
