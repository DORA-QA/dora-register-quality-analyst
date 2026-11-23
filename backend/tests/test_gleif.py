# SPDX-License-Identifier: EUPL-1.2
"""Branch feature/gleif-local: GLEIF checks against a local copy, updater and waiting screen.

The GLEIF copy used here is a small extract written for the test (same columns as the copy built
by tools/build_gleif.py); no network is used.
"""

import io
import json
import time
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from api.config import get_settings
from contracts.check_report import load_registry
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.gleif import GleifState
from contracts.messages import load_catalog, render_message
from gleif import updater
from gleif.layout import CURRENT, MANIFEST, installed_manifest
from gleif.status import read_status, write_status
from gleif.store import ParquetGleifStore
from rules.engine import RulesEngine
from rules.technical.gleif import CODES, EVALUATED_CODES, GleifRule
from tests.test_technical_rules import frame

LEI_OK = "5299000000000000A196"  # ISSUED, FR, renewal far away
LEI_LAPSED = "5299000000000000B263"
LEI_RETIRED = "5299000000000000C330"  # successor LEI_OK
LEI_DUE = "5299000000000000D494"  # ISSUED, renewal before 30/04/2027
LEI_DE = "5299000000000000E561"  # ISSUED, German
LEI_UNKNOWN = "5299000000000000F628"  # well formed, absent from the copy
LEI_PARENT = "5299000000000000G792"  # parent recorded in GLEIF
LEI_CHILD = "5299000000000000H859"  # entity whose GLEIF direct parent is LEI_PARENT
LEI_TYPE = "eba_qCO:qx2000"

RECORDS = [
    # lei, name, legal country, hq country, entity, registration, renewal, successor
    (LEI_OK, "ACME SERVICES SAS", "FR", "FR", "ACTIVE", "ISSUED", "2027-10-01", None),
    (LEI_LAPSED, "LAPSED SA", "FR", "FR", "ACTIVE", "LAPSED", "2025-01-05", None),
    (LEI_RETIRED, "OLD CO", "FR", "FR", "INACTIVE", "RETIRED", "2020-01-01", LEI_OK),
    (LEI_DUE, "DUE SOON SA", "FR", "FR", "ACTIVE", "ISSUED", "2027-02-13", None),
    (LEI_DE, "HKS GMBH", "DE", "DE", "ACTIVE", "ISSUED", "2028-01-01", None),
    (LEI_PARENT, "GROUPE PARENT SA", "FR", "FR", "ACTIVE", "ISSUED", "2027-12-01", None),
    (LEI_CHILD, "FILIALE SA", "FR", "FR", "ACTIVE", "ISSUED", "2027-12-01", None),
]
COLUMNS = (
    "lei",
    "legal_name",
    "legal_country",
    "hq_country",
    "entity_status",
    "registration_status",
    "next_renewal",
    "successor_lei",
)


def install_copy(root: Path, content_date: str = "2026-11-08T09:00:01Z") -> Path:
    folder = root / CURRENT
    folder.mkdir(parents=True, exist_ok=True)
    pl.DataFrame([dict(zip(COLUMNS, r, strict=True)) for r in RECORDS]).sort("lei").write_parquet(
        folder / "lei.parquet"
    )
    pl.DataFrame(
        {
            "child_lei": [LEI_CHILD, LEI_DE],
            "parent_lei": [LEI_PARENT, LEI_PARENT],
            "rel_type": ["IS_DIRECTLY_CONSOLIDATED_BY", "IS_ULTIMATELY_CONSOLIDATED_BY"],
            "rel_status": ["ACTIVE", "ACTIVE"],
            "reg_status": ["PUBLISHED", "PUBLISHED"],
        }
    ).write_parquet(folder / "rr.parquet")
    manifest = {
        "format": 1,
        "release": "gleif-test",
        "content_date": content_date,
        "files": {"lei.parquet": {"rows": len(RECORDS)}, "rr.parquet": {"rows": 2}},
    }
    (folder / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    return root


@pytest.fixture
def store(tmp_path: Path) -> ParquetGleifStore:
    return ParquetGleifStore(install_copy(tmp_path))


def provider(code: str, name: str = "ACME SERVICES SAS", country: str = "eba_GA:FR", parent=None):
    return {
        "c0010": code,
        "c0020": LEI_TYPE,
        "c0050": name,
        "c0060": name,
        "c0070": "eba_CT:x212",
        "c0080": country,
        "c0110": parent or code,
        "c0120": LEI_TYPE,
    }


def dataset(*providers: dict[str, str], entities=(), reference_date="2026-12-31") -> RoIDataset:
    tables = {"B_05.01": frame("B_05.01", *providers)}
    if entities:
        tables["B_01.02"] = frame("B_01.02", *entities)
    return RoIDataset("ZIP", PackageMetadata(reference_date=reference_date), tables)


def run(store, data: RoIDataset, today=date(2026, 11, 8)):
    return GleifRule(store, today=today).evaluate(data)


def by_code(messages) -> dict[str, list]:
    found: dict[str, list] = {}
    for message in messages:
        found.setdefault(message.code, []).append(message)
    return found


# ------------------------------------------------------------------ catalogue


def test_every_gleif_code_is_in_the_catalogue_and_the_registry() -> None:
    registry = {e["code"]: e for e in load_registry()}
    for code in CODES:
        assert code in load_catalog()
        assert registry[code]["category"] == "gleif"
    assert load_catalog()["GLF-001"]["official_codes"][0] == "EBA.VR_2"
    assert load_catalog()["GLF-005"]["official_codes"] == ["EBA.VR_16"]


# ------------------------------------------------------------------ rules


def test_a_compliant_register_gives_no_gleif_finding(store) -> None:
    assert run(store, dataset(provider(LEI_OK))) == []


def test_lei_absent_from_gleif_is_glf_001_with_its_eba_rule(store) -> None:
    found = by_code(run(store, dataset(provider(LEI_UNKNOWN))))
    assert set(found) == {"GLF-001"}
    message = found["GLF-001"][0]
    assert message.params["rule"] == "VR_71"
    assert message.params["copy_date"] == "2026-11-08"
    assert message.occurrences[0].value == LEI_UNKNOWN
    assert "VR_71" in render_message(message, "fr").explanation


def test_malformed_lei_is_left_to_the_format_checks(store) -> None:
    assert run(store, dataset(provider("5299000000000000A100"))) == []


def test_provider_typed_otherwise_is_not_looked_up(store) -> None:
    row = provider(LEI_UNKNOWN) | {"c0020": "eba_qCO:qx2003"}
    assert run(store, dataset(row)) == []


def test_retired_lei_is_glf_002_and_shows_the_successor(store) -> None:
    found = by_code(run(store, dataset(provider(LEI_RETIRED, name="OLD CO"))))
    assert set(found) == {"GLF-002"}
    assert f"→ {LEI_OK}" in found["GLF-002"][0].details


@pytest.mark.parametrize(
    "status", ["DUPLICATE", "ANNULLED", "PENDING_TRANSFER", "PENDING_ARCHIVAL"]
)
def test_duplicate_annulled_and_pending_lei_are_not_valid(tmp_path, status) -> None:
    """PO decision of 08/11/2026: these statuses count as invalid (GLF-002)."""
    root = install_copy(tmp_path)
    frame = pl.read_parquet(root / CURRENT / "lei.parquet")
    frame = frame.with_columns(
        pl.when(pl.col("lei") == LEI_OK)
        .then(pl.lit(status))
        .otherwise(pl.col("registration_status"))
        .alias("registration_status")
    )
    frame.write_parquet(root / CURRENT / "lei.parquet")
    found = by_code(run(ParquetGleifStore(root), dataset(provider(LEI_OK))))
    assert set(found) == {"GLF-002"}
    assert f"({status})" in found["GLF-002"][0].details


def test_lapsed_lei_is_glf_003(store) -> None:
    found = by_code(run(store, dataset(provider(LEI_LAPSED, name="LAPSED SA"))))
    assert set(found) == {"GLF-003"}
    assert load_catalog()["GLF-003"]["severity"] == "MINOR"


def test_renewal_before_30_april_after_the_reference_date_is_glf_004(store) -> None:
    found = by_code(run(store, dataset(provider(LEI_DUE, name="DUE SOON SA"))))
    assert set(found) == {"GLF-004"}
    assert found["GLF-004"][0].params["deadline"] == "2027-04-30"
    # No reference date: no deadline, no finding.
    assert run(store, dataset(provider(LEI_DUE, name="DUE SOON SA"), reference_date="")) == []


def test_country_of_a_provider_different_from_gleif_is_glf_006(store) -> None:
    row = provider(LEI_DE, name="HKS GMBH", parent=LEI_PARENT)
    found = by_code(run(store, dataset(row)))
    assert set(found) == {"GLF-006"}
    assert found["GLF-006"][0].occurrences[0].column == "c0080"


def test_country_of_an_entity_different_from_gleif_is_glf_005_vr_16(store) -> None:
    entity = {"c0010": LEI_DE, "c0020": "HKS GMBH", "c0030": "eba_GA:FR", "c0060": LEI_DE}
    found = by_code(run(store, dataset(provider(LEI_OK), entities=[entity])))
    assert set(found) == {"GLF-005"}
    assert found["GLF-005"][0].params["rule"] == "VR_12"


def test_name_far_from_the_legal_name_is_glf_007(store) -> None:
    found = by_code(run(store, dataset(provider(LEI_OK, name="SOCIETE SANS RAPPORT"))))
    assert set(found) == {"GLF-007"}
    # Case, accents, punctuation and a missing legal form are tolerated.
    assert run(store, dataset(provider(LEI_OK, name="Acme Services"))) == []


def test_direct_parent_different_from_gleif_is_glf_008(store) -> None:
    entity = {"c0010": LEI_CHILD, "c0020": "FILIALE SA", "c0030": "eba_GA:FR", "c0060": LEI_OK}
    found = by_code(run(store, dataset(provider(LEI_OK), entities=[entity])))
    assert set(found) == {"GLF-008"}
    assert found["GLF-008"][0].occurrences[0].column == "c0060"
    entity["c0060"] = LEI_PARENT
    assert run(store, dataset(provider(LEI_OK), entities=[entity])) == []


def test_ultimate_parent_of_every_provider_identified_by_lei_is_checked(store) -> None:
    """PO decision of 08/11/2026: 0110 must be the GLEIF ultimate parent for every LEI provider."""
    row = provider(LEI_DE, name="HKS GMBH", country="eba_GA:DE", parent=LEI_OK)
    found = by_code(run(store, dataset(row)))
    assert set(found) == {"GLF-009"}
    assert found["GLF-009"][0].occurrences[0].column == "c0110"
    # The provider declared as its own ultimate parent while GLEIF knows one.
    row["c0110"] = LEI_DE
    assert set(by_code(run(store, dataset(row)))) == {"GLF-009"}
    # Empty, or the right value typed otherwise than LEI.
    row["c0110"] = ""
    assert by_code(run(store, dataset(row)))["GLF-009"][0].occurrences[0].value == "∅"
    row["c0110"], row["c0120"] = LEI_PARENT, "eba_qCO:qx2001"
    assert "[qx2001]" in by_code(run(store, dataset(row)))["GLF-009"][0].occurrences[0].value
    row["c0120"] = LEI_TYPE
    assert run(store, dataset(row)) == []
    # GLEIF records no ultimate parent: nothing to compare with.
    assert run(store, dataset(provider(LEI_OK, parent=LEI_DE))) == []


def test_no_copy_installed_gives_glf_010_and_leaves_the_checks_not_evaluated(tmp_path) -> None:
    rule = GleifRule(ParquetGleifStore(tmp_path))
    result = RulesEngine(rules=[], extra=[rule]).run(dataset(provider(LEI_UNKNOWN)))
    assert [m.code for m in result.messages] == ["GLF-010"]
    assert result.blind_codes == set(EVALUATED_CODES)
    assert GleifRule(None).evaluate(dataset(provider(LEI_OK)))[0].code == "GLF-010"


def test_old_copy_is_glf_011(tmp_path) -> None:
    old = ParquetGleifStore(install_copy(tmp_path, "2026-10-01T09:00:00Z"))
    found = by_code(run(old, dataset(provider(LEI_OK))))
    assert set(found) == {"GLF-011"}
    assert found["GLF-011"][0].params["days"] == 38


def test_lookups_read_only_the_requested_lei(store) -> None:
    assert set(store.records({LEI_OK, LEI_UNKNOWN})) == {LEI_OK}
    assert store.records(set()) == {}
    assert store.parents({LEI_CHILD}, "IS_DIRECTLY_CONSOLIDATED_BY") == {LEI_CHILD: LEI_PARENT}


def test_coverage_counts_distinct_lei_not_cells(store) -> None:
    """A LEI reported in several tables is one LEI in the summary of the report."""
    from rules.technical.gleif import coverage

    entity = {"c0010": LEI_UNKNOWN, "c0020": "X", "c0030": "eba_GA:FR", "c0060": LEI_UNKNOWN}
    data = dataset(provider(LEI_UNKNOWN), provider(LEI_LAPSED, name="LAPSED SA"), entities=[entity])
    messages = run(store, data)
    found = coverage(data, messages, store.snapshot)
    assert (found.checked, found.absent, found.lapsed) == (2, 1, 1)
    assert sum(len(m.occurrences) for m in messages if m.code == "GLF-001") == 3


# ------------------------------------------------------------------ status


def test_status_follows_the_heartbeat_of_the_updater(tmp_path) -> None:
    started = time.time()
    # Nothing written yet, right after start-up: wait for the updater.
    assert read_status(tmp_path, started_epoch=started).state is GleifState.UPDATING
    # Nothing written long after start-up, nothing installed.
    assert read_status(tmp_path, started_epoch=started - 1000).state is GleifState.UNAVAILABLE
    write_status(tmp_path, GleifState.UPDATING, received_bytes=10, total_bytes=100)
    status = read_status(tmp_path, started_epoch=started)
    assert status.state is GleifState.UPDATING and status.total_bytes == 100
    # A silent updater (crashed) no longer blocks the tool.
    assert read_status(tmp_path, now=time.time() + 120).state is GleifState.UNAVAILABLE
    install_copy(tmp_path)
    write_status(tmp_path, GleifState.READY)
    assert read_status(tmp_path).state is GleifState.READY
    assert read_status(tmp_path).content_date == "2026-11-08T09:00:01Z"
    assert read_status(tmp_path, enabled=False).state is GleifState.DISABLED


# ------------------------------------------------------------------ updater


class FakeReleases:
    """Stands for GitHub: one release made of the files of a folder."""

    def __init__(self, folder: Path, tag: str = "gleif-20261108-0900", corrupt: bool = False):
        self.folder, self.tag, self.corrupt, self.downloads = folder, tag, corrupt, []

    def latest(self, prefix: str):
        names = ["manifest.json", "lei.parquet", "rr.parquet"]
        return {"tag_name": self.tag, "assets": [{"name": n, "url": n} for n in names]}

    def open_asset(self, asset):
        self.downloads.append(asset["name"])
        data = (self.folder / asset["name"]).read_bytes()
        if self.corrupt and asset["name"] == "rr.parquet":
            data += b"x"
        return io.BytesIO(data)


def published(tmp_path: Path) -> Path:
    """A release folder as written by tools/build_gleif.py (manifest with SHA-256)."""
    source = install_copy(tmp_path / "built") / CURRENT
    import hashlib

    manifest = json.loads((source / MANIFEST).read_text())
    for name in ("lei.parquet", "rr.parquet"):
        data = (source / name).read_bytes()
        manifest["files"][name].update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    (source / MANIFEST).write_text(json.dumps(manifest))
    return source


def test_updater_installs_the_latest_release_then_skips_it(tmp_path) -> None:
    source = FakeReleases(published(tmp_path))
    root = tmp_path / "volume"
    assert updater.update(root, source) == "gleif-20261108-0900"
    assert installed_manifest(root)["release"] == "gleif-20261108-0900"
    assert set(ParquetGleifStore(root).records({LEI_OK})) == {LEI_OK}
    source.downloads.clear()
    updater.update(root, source)
    assert source.downloads == ["manifest.json"]  # already installed: data not downloaded again


def test_updater_refuses_a_corrupted_file_and_keeps_the_installed_copy(tmp_path) -> None:
    root = tmp_path / "volume"
    updater.update(root, FakeReleases(published(tmp_path)))
    broken = FakeReleases(published(tmp_path / "second"), tag="gleif-new", corrupt=True)
    broken.folder = published(tmp_path / "third")
    # Force a different manifest so that the update is attempted.
    manifest = json.loads((broken.folder / MANIFEST).read_text())
    manifest["content_date"] = "2026-11-09T09:00:00Z"
    manifest["files"]["lei.parquet"]["rows"] = 99
    (broken.folder / MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(updater.UpdateError) as failure:
        updater.update(root, broken)
    assert failure.value.reason == "checksum"
    assert installed_manifest(root)["release"] == "gleif-20261108-0900"
    assert not list(root.glob(".incoming-*"))


def test_updater_main_never_leaves_the_status_on_updating(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ROI_GLEIF_DIR", str(tmp_path))

    def unreachable(self, prefix):
        raise updater.UpdateError("network")

    monkeypatch.setattr(updater.GitHubReleases, "latest", unreachable)
    assert updater.main() == 0
    written = json.loads((tmp_path / "status.json").read_text())
    assert written["state"] == "UNAVAILABLE" and written["last_error"] == "network"


def test_hold_keeps_the_state_updating_for_acceptance_tests(tmp_path, monkeypatch) -> None:
    states = []
    monkeypatch.setenv("ROI_GLEIF_DIR", str(tmp_path))
    monkeypatch.setenv("ROI_GLEIF_HOLD_SECONDS", "0.3")
    monkeypatch.setattr(updater, "write_status", lambda root, state, **fields: states.append(state))

    def unreachable(self, prefix):
        raise updater.UpdateError("network")

    monkeypatch.setattr(updater.GitHubReleases, "latest", unreachable)
    updater.main()
    assert states[0] is GleifState.UPDATING and states[-1] is GleifState.UNAVAILABLE


# ------------------------------------------------------------------ API


@pytest.fixture
def gleif_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("ROI_GLEIF_ENABLED", "true")
    monkeypatch.setenv("ROI_GLEIF_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_status_endpoint_is_disabled_by_default(client) -> None:
    assert client.get("/api/gleif/status").json()["state"] == "DISABLED"


def test_import_is_refused_while_the_copy_is_updating(gleif_settings, valid_zip) -> None:
    from fastapi.testclient import TestClient

    from api.main import app
    from tests.factories import CLIENT_HEADERS

    write_status(gleif_settings, GleifState.UPDATING, received_bytes=1, total_bytes=2)
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        assert client.get("/api/gleif/status").json()["state"] == "UPDATING"
        with open(valid_zip, "rb") as handle:
            answer = client.post(
                "/api/import?lang=fr", files={"file": ("p.zip", handle, "application/zip")}
            )
        assert answer.status_code == 503
        assert "mise à jour" in answer.json()["detail"]
        install_copy(gleif_settings)
        write_status(gleif_settings, GleifState.READY)
        assert client.get("/api/gleif/status").json()["release"] == "gleif-test"
        with open(valid_zip, "rb") as handle:
            answer = client.post(
                "/api/import", files={"file": ("p.zip", handle, "application/zip")}
            )
        assert answer.status_code == 200
        # The summary at the top of the report tells how the LEI fared against GLEIF.
        assert answer.json()["overview"]["gleif"].startswith("GLEIF check (copy of 2026-11-08)")


# ------------------------------------------------------------------ deployment


def _compose() -> dict:
    import yaml

    root = Path(__file__).resolve().parents[2]
    return yaml.safe_load((root / "docker-compose.yml").read_text(encoding="utf-8"))


def test_only_the_updater_goes_online_and_the_backend_reads_the_copy_read_only() -> None:
    services = _compose()["services"]
    updater_service = services["gleif-updater"]
    assert updater_service["networks"] == ["default"], "the updater never joins the backend network"
    assert "ports" not in updater_service
    assert updater_service["read_only"] is True and updater_service["restart"] == "no"
    assert "gleif-data:/data/gleif:ro" in services["backend"]["volumes"]
    assert services["backend"]["environment"]["ROI_GLEIF_ENABLED"] == "true"


# ------------------------------------------------------------------ build script

LEI_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<lei:LEIData xmlns:lei="http://www.gleif.org/data/schema/leidata/2016">
<lei:LEIHeader><lei:ContentDate>2026-11-08T09:00:01Z</lei:ContentDate></lei:LEIHeader>
<lei:LEIRecords>
<lei:LEIRecord xmlns:lei="http://www.gleif.org/data/schema/leidata/2016"><lei:LEI>{LEI_OK}</lei:LEI>
<lei:Entity><lei:LegalName xml:lang="fr">ACME SERVICES SAS</lei:LegalName>
<lei:LegalAddress><lei:Country>FR</lei:Country></lei:LegalAddress>
<lei:HeadquartersAddress><lei:Country>FR</lei:Country></lei:HeadquartersAddress>
<lei:EntityStatus>ACTIVE</lei:EntityStatus></lei:Entity>
<lei:Registration><lei:LastUpdateDate>2026-01-01T00:00:00Z</lei:LastUpdateDate>
<lei:RegistrationStatus>PENDING_TRANSFER</lei:RegistrationStatus>
<lei:NextRenewalDate>2027-10-01T00:00:00Z</lei:NextRenewalDate></lei:Registration></lei:LEIRecord>
<lei:LEIRecord xmlns:lei="http://www.gleif.org/data/schema/leidata/2016"><lei:LEI>{LEI_OK}</lei:LEI>
<lei:Entity><lei:LegalName>ACME SERVICES SAS</lei:LegalName>
<lei:EntityStatus>ACTIVE</lei:EntityStatus>
<lei:SuccessorEntity><lei:SuccessorLEI>{LEI_CHILD}</lei:SuccessorLEI></lei:SuccessorEntity></lei:Entity>
<lei:Registration><lei:LastUpdateDate>2025-01-01T00:00:00Z</lei:LastUpdateDate>
<lei:RegistrationStatus>ISSUED</lei:RegistrationStatus>
<lei:NextRenewalDate>2027-10-01T00:00:00Z</lei:NextRenewalDate></lei:Registration></lei:LEIRecord>
</lei:LEIRecords></lei:LEIData>
"""
RR_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<rr:RelationshipData xmlns:rr="http://www.gleif.org/data/schema/rr/2016">
<rr:Header><rr:ContentDate>2026-11-08T09:00:01Z</rr:ContentDate></rr:Header>
<rr:RelationshipRecords><rr:RelationshipRecord><rr:Relationship>
<rr:StartNode><rr:NodeID>{LEI_CHILD}</rr:NodeID></rr:StartNode><rr:EndNode><rr:NodeID>{LEI_PARENT}</rr:NodeID></rr:EndNode>
<rr:RelationshipType>IS_DIRECTLY_CONSOLIDATED_BY</rr:RelationshipType>
<rr:RelationshipStatus>ACTIVE</rr:RelationshipStatus></rr:Relationship>
<rr:Registration><rr:RegistrationStatus>PUBLISHED</rr:RegistrationStatus></rr:Registration>
</rr:RelationshipRecord></rr:RelationshipRecords></rr:RelationshipData>
"""


def test_build_script_writes_a_copy_the_store_and_the_updater_accept(tmp_path) -> None:
    import zipfile

    from tools import build_gleif

    (tmp_path / "lei2.xml").write_text(LEI_XML, encoding="utf-8")
    with zipfile.ZipFile(tmp_path / "rr.zip", "w") as archive:
        archive.writestr("rr.xml", RR_XML)
    out = tmp_path / "release"
    build_gleif.main(
        ["--lei", str(tmp_path / "lei2.xml"), "--rr", str(tmp_path / "rr.zip"), "--out", str(out)]
    )
    manifest = json.loads((out / MANIFEST).read_text())
    assert manifest["content_date"] == "2026-11-08T09:00:01Z"
    assert manifest["files"]["lei.parquet"]["rows"] == 1  # duplicate removed, ISSUED kept
    root = tmp_path / "volume"
    updater.update(root, FakeReleases(out))
    record = ParquetGleifStore(root).records({LEI_OK})[LEI_OK]
    assert record.registration_status == "ISSUED" and record.successor_lei == LEI_CHILD
    assert ParquetGleifStore(root).parents({LEI_CHILD}, "IS_DIRECTLY_CONSOLIDATED_BY") == {
        LEI_CHILD: LEI_PARENT
    }
