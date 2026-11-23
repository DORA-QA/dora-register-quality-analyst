# SPDX-License-Identifier: EUPL-1.2
"""Contract of the local GLEIF reference data (branch feature/gleif-local).

The rules never read the GLEIF files themselves: they receive an object that follows
``IGleifLookup``. The data is a local copy (Parquet files built from the GLEIF files and published
on the repository); the analysis itself never goes on the internet.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

# Registration statuses of the GLEIF Common Data File (LEI-CDF 3.1).
ISSUED = "ISSUED"
LAPSED = "LAPSED"
# Not a valid LEI for the register (PO decision of 08/11/2026: DUPLICATE, ANNULLED and every
# PENDING_* status count as invalid, like RETIRED and MERGED).
NOT_VALID = frozenset(
    {
        "RETIRED",
        "MERGED",
        "ANNULLED",
        "DUPLICATE",
        "PENDING_TRANSFER",
        "PENDING_ARCHIVAL",
        "PENDING_VALIDATION",
    }
)
ACTIVE_ENTITY = "ACTIVE"

# Relationship types of the RR-CDF used by the rules.
DIRECT_PARENT = "IS_DIRECTLY_CONSOLIDATED_BY"
ULTIMATE_PARENT = "IS_ULTIMATELY_CONSOLIDATED_BY"


class GleifState(StrEnum):
    """State of the local copy, as shown to the reader."""

    # The updater is downloading a new copy: no register is accepted meanwhile.
    UPDATING = "UPDATING"
    # A copy is installed and readable.
    READY = "READY"
    # No copy is installed (first start without network, or no token): GLEIF checks are skipped.
    UNAVAILABLE = "UNAVAILABLE"
    # The feature is switched off (ROI_GLEIF_ENABLED=false).
    DISABLED = "DISABLED"


@dataclass(frozen=True)
class GleifRecord:
    """What the rules need about one LEI. Every field may be missing in the GLEIF data."""

    lei: str
    legal_name: str | None
    legal_country: str | None
    hq_country: str | None
    entity_status: str | None
    registration_status: str | None
    next_renewal: str | None  # yyyy-mm-dd
    successor_lei: str | None


@dataclass(frozen=True)
class GleifSnapshot:
    """Identity of the installed copy: shown next to every GLEIF finding."""

    content_date: str  # date and time of the GLEIF publication (UTC, ISO 8601)
    release: str  # tag of the release on the repository
    lei_count: int


class IGleifLookup(Protocol):
    @property
    def snapshot(self) -> GleifSnapshot | None:
        """None when no copy is installed."""
        ...

    def records(self, leis: set[str]) -> dict[str, GleifRecord]:
        """Records of the LEI found in the copy (the others are absent from the result)."""
        ...

    def parents(self, leis: set[str], relationship: str) -> dict[str, str]:
        """Child LEI -> parent LEI, for the active relationships of the given type."""
        ...


@dataclass(frozen=True)
class GleifCoverage:
    """What the summary at the top of the report says about the GLEIF verification."""

    # False when no copy is installed (the LEI were not checked).
    available: bool
    # Distinct well-formed LEI looked up in the copy.
    checked: int
    # Date of the GLEIF publication of the copy used (yyyy-mm-dd), None without copy.
    copy_date: str | None
    # Distinct LEI by kind of problem (GLF-001 to GLF-004), and differences of country, name or
    # parent (GLF-005 to GLF-009, one per cell).
    absent: int = 0
    invalid: int = 0
    lapsed: int = 0
    due: int = 0
    mismatches: int = 0
