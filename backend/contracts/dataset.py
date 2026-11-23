# SPDX-License-Identifier: EUPL-1.2
"""Core business object of the product: the imported register."""

from dataclasses import dataclass, field

import polars as pl


@dataclass
class PackageMetadata:
    """What the package says about itself. Every field may be missing."""

    source_type: str = "UNKNOWN"  # XML or ZIP
    channel: str | None = None  # extraction strategy used for an XML envelope
    package_name: str | None = None  # name of the root folder of the package
    taxonomy_entry_point: str | None = None
    taxonomy_version: str | None = None  # e.g. "4.0"
    module_code: str | None = None  # e.g. "DORA010100"
    entity_lei: str | None = None
    reporting_scope: str | None = None  # IND or CON
    country: str | None = None
    reference_date: str | None = None  # yyyy-mm-dd
    base_currency: str | None = None
    envelope_sender_lei: str | None = None
    envelope_domain: str | None = None
    envelope_recipient: str | None = None  # None when the envelope administration was not read


@dataclass
class RoIDataset:
    """Register of information loaded in memory.

    ``tables`` maps a table code (``B_01.01``) to a Polars DataFrame whose columns
    are all text, plus ``_row``: the 1-based number of the data row in the CSV.
    """

    source_type: str
    package_metadata: PackageMetadata
    tables: dict[str, pl.DataFrame] = field(default_factory=dict)
