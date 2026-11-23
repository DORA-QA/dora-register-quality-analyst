# SPDX-License-Identifier: EUPL-1.2
"""Builds the central business object from the import results."""

from contracts.dataset import PackageMetadata, RoIDataset
from contracts.import_results import CsvImportResult


class DatasetBuilder:
    def build(self, metadata: PackageMetadata, csv_result: CsvImportResult) -> RoIDataset:
        return RoIDataset(
            source_type=metadata.source_type,
            package_metadata=metadata,
            tables=dict(csv_result.tables),
        )
