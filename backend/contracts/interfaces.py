# SPDX-License-Identifier: EUPL-1.2
"""Contracts of the engines (see base.txt, sections 13 to 19).

Engines implement these protocols and depend on nothing but ``contracts``.
"""

from typing import Protocol

from contracts.dataset import PackageMetadata, RoIDataset
from contracts.import_results import (
    CsvImportResult,
    ExtractedZip,
    FileTypeResult,
    PackageValidationResult,
    XmlValidationResult,
    ZipValidationResult,
)


class IFileTypeDetector(Protocol):
    def detect(self, file_path: str) -> FileTypeResult: ...


class IXmlValidator(Protocol):
    def validate(self, xml_file: str) -> XmlValidationResult: ...


class IXmlZipExtractor(Protocol):
    def extract_zip(self, xml_file: str) -> ExtractedZip: ...


class IZipValidator(Protocol):
    def validate(self, zip_file: str) -> ZipValidationResult: ...


class IPackageValidator(Protocol):
    def validate(self, zip_file: str) -> PackageValidationResult: ...


class ICsvImporter(Protocol):
    def load(self, zip_file: str) -> CsvImportResult: ...


class IDatasetBuilder(Protocol):
    def build(self, metadata: PackageMetadata, csv_result: CsvImportResult) -> RoIDataset: ...
