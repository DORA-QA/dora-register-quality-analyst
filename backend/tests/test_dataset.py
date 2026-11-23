# SPDX-License-Identifier: EUPL-1.2
from contracts.dataset import PackageMetadata
from dataset.builder import DatasetBuilder
from dataset.store import DatasetStore
from import_engine.csv_importer import CsvImporter


def build(valid_zip):
    csv_result = CsvImporter().load(valid_zip)
    return DatasetBuilder().build(PackageMetadata(source_type="ZIP"), csv_result)


def test_dataset_exposes_tables_by_code(valid_zip) -> None:
    dataset = build(valid_zip)

    assert dataset.source_type == "ZIP"
    assert dataset.tables["B_01.01"].height == 1
    assert dataset.tables["B_05.01"].height == 2


def test_store_keeps_one_dataset_at_a_time(valid_zip) -> None:
    store = DatasetStore()
    store.put("first", build(valid_zip))
    store.put("second", build(valid_zip))

    assert store.get("first") is None
    assert store.get("second") is not None

    store.purge()
    assert store.get("second") is None


def test_store_drops_an_expired_dataset(valid_zip) -> None:
    store = DatasetStore(ttl_seconds=-1)
    store.put("old", build(valid_zip))

    assert store.get("old") is None
