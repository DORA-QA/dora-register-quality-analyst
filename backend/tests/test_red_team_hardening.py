# SPDX-License-Identifier: EUPL-1.2
"""Corrections de l'analyse red team du 28/10/2026 (docs/red-team-2026-10-28.md)."""

import hashlib
import zipfile
from pathlib import Path

import polars as pl
from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from api.services.import_service import ImportService
from contracts.dataset import PackageMetadata, RoIDataset
from dataset.store import DatasetStore
from rules.engine import RULE_FAILED_CODE, RulesEngine
from tests.factories import CLIENT_HEADERS

ROOT = Path(__file__).resolve().parents[2]


class _Broken:
    id = "BROKEN-RULE"

    def evaluate(self, dataset):
        raise ValueError("valeur du registre : ACME SECRET")


class _Fine:
    id = "FINE-RULE"

    def evaluate(self, dataset):
        return []


def _dataset() -> RoIDataset:
    return RoIDataset(
        source_type="ZIP",
        package_metadata=PackageMetadata(),
        tables={"B_01.01": pl.DataFrame({"c0010": ["X"]})},
    )


def test_a_failing_rule_does_not_stop_the_others_and_is_reported(caplog):
    result = RulesEngine([_Broken(), _Fine()]).run(_dataset())
    assert result.rules_run == 2
    assert [m.code for m in result.messages] == [RULE_FAILED_CODE]
    assert result.messages[0].params == {"rule": "BROKEN-RULE"}
    # The log names the rule and the error type, never the error text (register data).
    assert "BROKEN-RULE" in caplog.text
    assert "ACME" not in caplog.text


def test_a_dotted_file_name_is_answered_not_crashed():
    with TestClient(create_app(), headers=CLIENT_HEADERS, raise_server_exceptions=False) as client:
        for name in ("..", ".", "a/../.."):
            response = client.post("/api/import", files={"file": (name, b"not a register")})
            assert response.status_code == 200, name
            assert response.json()["status"] == "FAILED"


def test_the_last_outcome_and_the_dataset_expire(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("time.monotonic", lambda: clock[0])
    store = DatasetStore(ttl_seconds=60)
    service = ImportService(Settings(dataset_ttl_minutes=1), store)
    sample = ROOT / "backend" / "tests" / "golden" / "golden.sample.zip"
    outcome = service.run(sample, sample.name)
    assert service.last_outcome(outcome.import_id) is outcome
    clock[0] += 61
    service.expire()
    assert service.last_outcome(outcome.import_id) is None
    assert store.get(outcome.import_id) is None


def _contents(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        return {
            name.split("/", 1)[-1]: hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if not name.endswith("/")
        }


def test_the_two_copies_of_the_golden_stay_identical():
    published = next((ROOT / "sample-data").glob("529900P784EKW7VFMQ21*.zip"))
    tested = ROOT / "backend" / "tests" / "golden" / "golden.sample.zip"
    assert _contents(published) == _contents(tested)
