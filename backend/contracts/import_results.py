# SPDX-License-Identifier: EUPL-1.2
"""Results exchanged between the steps of the import chain."""

from dataclasses import dataclass, field

import polars as pl

from contracts.dataset import PackageMetadata
from contracts.messages import ValidationMessage, has_blocker, split_messages

FILE_TYPE_XML = "XML"
FILE_TYPE_ZIP = "ZIP"
FILE_TYPE_UNKNOWN = "UNKNOWN"


@dataclass
class _WithMessages:
    """Base of the results: ``errors`` and ``warnings`` are views on ``messages``."""

    messages: list[ValidationMessage] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not has_blocker(self.messages)

    @property
    def errors(self) -> list[ValidationMessage]:
        return split_messages(self.messages)[0]

    @property
    def warnings(self) -> list[ValidationMessage]:
        return split_messages(self.messages)[1]


@dataclass
class FileTypeResult:
    detected_type: str  # XML, ZIP or UNKNOWN


@dataclass
class XmlValidationResult(_WithMessages):
    root_tag: str | None = None
    xsd_checked: bool = False


@dataclass
class ExtractedZip(_WithMessages):
    zip_path: str | None = None
    strategy: str | None = None
    sender_lei: str | None = None
    domain: str | None = None
    # Value of <To>; None when the administration block was not read.
    recipient: str | None = None


@dataclass
class ZipValidationResult(_WithMessages):
    file_count: int = 0
    package_size: int = 0  # uncompressed size in bytes
    inventory: list[str] = field(default_factory=list)


@dataclass
class PackageValidationResult(_WithMessages):
    taxonomy_version: str | None = None
    rt_detected: list[str] = field(default_factory=list)
    missing_rt: list[str] = field(default_factory=list)
    metadata: PackageMetadata = field(default_factory=PackageMetadata)


@dataclass
class TableSummary:
    code: str
    file: str
    rows: int
    columns: int


@dataclass
class CsvImportResult(_WithMessages):
    tables: dict[str, pl.DataFrame] = field(default_factory=dict)
    summaries: list[TableSummary] = field(default_factory=list)

    @property
    def total_tables(self) -> int:
        return len(self.tables)

    @property
    def total_rows(self) -> int:
        return sum(summary.rows for summary in self.summaries)
