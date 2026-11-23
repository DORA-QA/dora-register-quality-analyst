# SPDX-License-Identifier: EUPL-1.2
"""The golden files of sample-data/ raise only the findings admitted by their manifest."""

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.factories import CLIENT_HEADERS
from tests.make_samples import MULTI_DEFECT_CASES, multi_defect_package

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample-data"
GOLDEN_FILES = sorted(SAMPLE_DIR.glob("529900P784EKW7VFMQ21.CON_*.zip")) + [
    SAMPLE_DIR / "golden-onegate.sample.xml"
]


def test_golden_files_present() -> None:
    assert all(path.exists() for path in GOLDEN_FILES)
    assert len(GOLDEN_FILES) == 2


def admitted_findings() -> dict[str, int]:
    """Findings the golden raises by decision of the PO (manifest): code -> occurrences."""
    manifest = json.loads((SAMPLE_DIR / "golden-manifest.sample.json").read_text("utf-8"))
    return {f["code"]: f["occurrences"] for f in manifest["expected_findings"]["current_engine"]}


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda p: p.suffix)
def test_golden_without_unexpected_finding(path: Path) -> None:
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        response = client.post("/api/import", files={"file": (path.name, path.read_bytes())})
    body = response.json()
    assert response.status_code == 200
    found = {m["code"]: m["occurrences_total"] for m in body["messages"]}
    assert found == admitted_findings()
    assert all(m["severity"] in ("MINOR", "INFO") for m in body["messages"])
    assert body["status"] in ("SUCCESS", "SUCCESS_WITH_WARNINGS")


def _import(path: Path) -> dict:
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        return client.post("/api/import", files={"file": (path.name, path.read_bytes())}).json()


def test_package_with_several_categories_of_defects() -> None:
    """Brief §16 (last recette package) and §9.2: several categories, several findings per row."""
    body = _import(SAMPLE_DIR / "package-with-data-defects.sample.zip")
    found = {m["code"] for m in body["messages"]}

    assert body["status"] == "FAILED"
    # Header, keys (805, 806, 807), LEI and EUID, as described in sample-data/README.md.
    assert {"DAT-001", "DAT-003", "DAT-004", "DAT-005", "DAT-010", "DAT-011", "DAT-012"} <= found
    rows: dict[tuple, set[str]] = {}
    for message in body["messages"]:
        for place in message["occurrences"]:
            if place["row"]:
                rows.setdefault((place["table"], place["row"]), set()).add(message["code"])
    # Several findings on one same row are all kept, each with its own code.
    assert any(len(codes) > 1 for codes in rows.values()), rows


def test_envelope_carrying_a_defective_package() -> None:
    """Brief §9.2: an XML envelope whose ZIP is technically non-conforming."""
    body = _import(SAMPLE_DIR / "onegate-envelope-with-defects.sample.xml")
    found = {m["code"] for m in body["messages"]}

    assert body["status"] == "FAILED" and body["source_type"] == "XML"
    assert {"ENV-006", "ENV-009"} <= found  # envelope
    assert {"PKG-007", "CSV-005"} <= found  # package and tables inside it


def test_no_register_value_is_written_to_the_logs(caplog) -> None:
    """Brief §10: logs hold codes and counts, never the values of the register."""
    caplog.set_level("DEBUG")
    body = _import(SAMPLE_DIR / "package-with-data-defects.sample.zip")
    values = {
        place["value"]
        for message in body["messages"]
        for place in message["occurrences"]
        if place["value"] and len(place["value"].strip()) >= 4
    }

    assert values, "the sample must expose values to look for"
    assert "status=FAILED" in caplog.text, "the import log must have been captured"
    assert body["metadata"]["entity_lei"]
    leaked = [v for v in values | {body["metadata"]["entity_lei"]} if v.strip() in caplog.text]
    assert leaked == []


def test_golden_manifest_matches_the_package_and_the_findings() -> None:
    """Brief Sprint 3 §16.1: the golden documents its scenarios and its admitted findings."""
    import json
    import zipfile

    manifest = json.loads((SAMPLE_DIR / "golden-manifest.sample.json").read_text("utf-8"))
    golden = SAMPLE_DIR / manifest["golden"]
    assert golden.exists()
    assert [s["id"] for s in manifest["scenarios"]] == [f"G{n}" for n in range(1, 10)]

    reports = {
        name.rsplit("/", 1)[-1]: zipfile.ZipFile(golden).read(name).decode("utf-8-sig")
        for name in zipfile.ZipFile(golden).namelist()
        if "/reports/b_" in name
    }
    # Each scenario quotes identifiers that must really be in the package.
    for code in (
        "529900R81VAA8RCKLQ52",
        "529900D18SWZVAN3CV11",
        "529900JULHLZDL9AS417",
        "X4RTBPFW4",
        "CONTRAT PARTAGE",
    ):
        assert any(code in content for content in reports.values()), code

    body = _import(golden)
    assert {m["code"] for m in body["messages"]} == set(admitted_findings())


def test_concentration_indicators_are_returned_by_the_api() -> None:
    """Brief Sprint 3 §13: indicators in the answer of the import, no display."""
    body = _import(GOLDEN_FILES[0])
    indicators = body["concentration"]
    assert (indicators["basis"], indicators["rows"], indicators["providers_count"]) == (
        "B_02.02",
        17,
        6,
    )
    assert indicators["hhi"] == 2872.0
    assert indicators["critical_functions"] == 2
    assert indicators["single_provider_critical_functions"] == []
    assert sum(item["rows"] for item in indicators["by_service_type"]["items"]) == 17


def test_no_concentration_without_b_02_02() -> None:
    body = _import(SAMPLE_DIR / "package-with-defects.sample.zip")
    assert body["concentration"] is None


MULTI_DEFECT_MANIFEST = SAMPLE_DIR / "package-multi-defects.manifest.sample.json"


def _members(content: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {i.filename: archive.read(i) for i in archive.infolist() if not i.is_dir()}


def test_multi_defect_package_matches_its_manifest() -> None:
    """Brief Sprint 3 §16.3: expected codes, findings and occurrences, verified automatically."""
    manifest = json.loads(MULTI_DEFECT_MANIFEST.read_text(encoding="utf-8"))
    package = SAMPLE_DIR / manifest["package"]
    assert [m["case"] for m in manifest["mutations"]] == list(MULTI_DEFECT_CASES)
    # The file is the one the generator builds (same members; ZIP dates aside).
    assert _members(package.read_bytes()) == _members(multi_defect_package())

    body = _import(package)
    assert body["status"] == manifest["expected"]["status"]
    found: dict[str, dict] = {}
    for message in body["messages"]:
        entry = found.setdefault(
            message["code"],
            {
                "code": message["code"],
                "severity": message["severity"],
                "findings": 0,
                "occurrences": 0,
            },
        )
        entry["findings"] += 1
        entry["occurrences"] += message["occurrences_total"] or len(message["occurrences"])
    expected = {f["code"]: f for f in manifest["expected"]["findings"]}
    assert found == expected
    # Every mutation is detected, and every code beyond them is an explained exception.
    targeted = {m["code"] for m in manifest["mutations"]}
    explained = {e["code"] for e in manifest["exceptions"]}
    assert targeted <= set(found)
    assert set(found) - targeted <= explained
