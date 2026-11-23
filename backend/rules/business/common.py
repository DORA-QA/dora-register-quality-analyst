# SPDX-License-Identifier: EUPL-1.2
"""Shared helpers of the Sprint 3 rules (consistency between tables, business rules).

A rule reads small reference tables (B_01.02, B_05.01) as dictionaries keyed by code, and
compares values exactly as reported, except names, which are compared after
normalisation (``normalise_name``). Values reach the answer through the structured
occurrences only, never the logs.
"""

import re
import unicodedata

from contracts.tables import ROW_COLUMN, by_code, rows

__all__ = ["ROW_COLUMN", "by_code", "rows"]  # re-exported for the rules of this package
ULTIMATE_PARENT = "eba_RP:x53"
INTRA_GROUP_PROVIDER = "eba_CT:x317"
_NOT_ALNUM = re.compile(r"[^0-9a-z]+")


def normalise_name(name: str) -> str:
    """Case, accents, punctuation and extra spaces removed.

    'Caisse des Dépôts' -> 'caisse des depots'.
    """
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _NOT_ALNUM.sub(" ", plain).strip()
