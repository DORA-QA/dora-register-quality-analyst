# SPDX-License-Identifier: EUPL-1.2
import tempfile
from pathlib import Path

from api.services.workspace import PREFIX
from tests import factories

ZIP_NAME = f"{factories.PACKAGE_NAME}.zip"


def post(client, name: str, content: bytes):
    return client.post("/api/import", files={"file": (name, content)})


def temp_folders() -> list[Path]:
    return list(Path(tempfile.gettempdir()).glob(f"{PREFIX}*"))


def test_import_of_a_valid_zip(client) -> None:
    body = post(client, ZIP_NAME, factories.build_zip()).json()

    assert body["status"] == "SUCCESS"
    assert body["source_type"] == "ZIP"
    assert (body["tables_loaded"], body["rows_loaded"]) == (15, 4)
    assert body["dataset_available"] is True
    assert body["metadata"]["entity_lei"] == factories.LEI
    assert body["metadata"]["taxonomy_version"] == "4.0"
    assert body["tables"][0] == {
        "code": "B_01.01",
        "file": "b_01.01.csv",
        "rows": 1,
        "columns": 6,
    }
    assert _unexpected(body) == []


def test_import_of_a_valid_envelope(client) -> None:
    body = post(client, "delivery.xml", factories.build_envelope()).json()

    assert body["status"] == "SUCCESS"
    assert body["source_type"] == "XML"
    assert body["metadata"]["channel"] == "ACPR_ONEGATE"
    assert body["metadata"]["envelope_domain"] == "DRB"
    assert body["tables_loaded"] == 15
    assert _unexpected(body) == []
    assert [s["status"] for s in body["steps"]] == ["OK"] * 8
    assert body["steps"][0] == {"key": "detection", "name": "File type detection", "status": "OK"}


def test_findings_are_explained_and_referenced(client) -> None:
    files = factories.default_files()
    files["reports/FilingIndicators.csv"] = files["reports/FilingIndicators.csv"].replace(
        b"B_99.01,true\n", b""
    )
    files["reports/b_02.01.csv"] = b"\xef\xbb\xbf" + files["reports/b_02.01.csv"]

    body = post(client, ZIP_NAME, factories.build_zip(files)).json()

    assert body["status"] == "FAILED"
    assert body["missing_rt"] == []
    assert body["counts"] == {
        "blocker": 1,
        "major": 0,
        "minor": 1,
        "info": 1,
    }  # DQ-004 on the minimal package
    # The import went on: the tables that exist are loaded and kept.
    assert body["tables_loaded"] == 15 and body["dataset_available"] is True
    blocker = body["messages"][0]
    assert blocker["code"] == "PKG-011" and blocker["severity"] == "BLOCKER"
    assert blocker["explanation"] and blocker["recommendation"]
    assert "Compare it with the list of the 15 templates" in blocker["expert_advice"]
    assert blocker["reference"]["type"] == "regulatory"


def test_envelope_sender_differs_from_package_entity(client) -> None:
    envelope = factories.build_envelope(sender="OTHERLEI000000000099")

    body = post(client, "delivery.xml", envelope).json()

    assert body["status"] == "FAILED"
    env009 = next(m for m in body["messages"] if m["code"] == "ENV-009")
    assert env009["severity"] == "BLOCKER"


def test_envelope_without_onegate_namespace_is_blocking(client) -> None:
    envelope = factories.build_envelope().replace(b' xmlns="http://www.onegate.eu/2010-01-01"', b"")

    body = post(client, "delivery.xml", envelope).json()

    assert body["status"] == "FAILED"
    env011 = next(m for m in body["messages"] if m["code"] == "ENV-011")
    assert env011["severity"] == "BLOCKER"
    assert env011["reference"]["type"] == "official_guide"
    assert body["tables_loaded"] == 0


def test_namespace_declared_on_the_root_is_also_accepted(client) -> None:
    namespace = b'xmlns="http://www.onegate.eu/2010-01-01"'
    envelope = factories.build_envelope()
    envelope = envelope.replace(b"<XbrlDelivery>", b"<XbrlDelivery " + namespace + b">")
    envelope = envelope.replace(
        b"<XbrlDeclarationReport " + namespace + b">", b"<XbrlDeclarationReport>"
    )

    body = post(client, "delivery.xml", envelope).json()

    assert body["status"] == "SUCCESS"


def test_envelope_in_another_namespace_is_blocking(client) -> None:
    envelope = factories.build_envelope().replace(b"onegate.eu/2010-01-01", b"example.org/other")

    body = post(client, "delivery.xml", envelope).json()

    assert "ENV-011" in [m["code"] for m in body["messages"]]


def test_unknown_and_empty_files(client) -> None:
    unknown = post(client, "notes.zip", b"plain text").json()
    empty = post(client, "empty.zip", b"").json()

    assert (unknown["status"], unknown["messages"][0]["code"]) == ("FAILED", "FILE-001")
    assert (empty["status"], empty["messages"][0]["code"]) == ("FAILED", "FILE-002")
    assert unknown["dataset_available"] is False


def test_malformed_xml_stops_the_chain(client) -> None:
    body = post(client, "delivery.xml", b"<XbrlDelivery><a></XbrlDelivery>").json()

    assert body["status"] == "FAILED"
    statuses = {s["key"]: s["status"] for s in body["steps"]}
    assert statuses["xml_validation"] == "FAILED"
    assert statuses["extraction"] == "SKIPPED"


def test_file_too_large_is_refused(client, monkeypatch) -> None:
    from api.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)

    assert post(client, ZIP_NAME, factories.build_zip()).status_code == 413
    refused = client.post("/api/import?lang=fr", files={"file": (ZIP_NAME, factories.build_zip())})
    assert refused.json()["detail"] == "Le fichier dépasse la limite de 0 Mo."


def test_no_temporary_file_survives_an_import(client) -> None:
    post(client, ZIP_NAME, factories.build_zip())
    post(client, "delivery.xml", factories.build_envelope())
    post(client, "delivery.xml", b"<broken")

    assert temp_folders() == []


def test_the_last_two_imports_can_be_read_again_and_only_the_last_register_is_kept(client) -> None:
    """RT-13 (decision A5, 02/11/2026): two tabs no longer erase each other; the register
    itself stays one at a time."""
    first = post(client, ZIP_NAME, factories.build_zip()).json()["import_id"]
    second = post(client, ZIP_NAME, factories.build_zip()).json()["import_id"]

    assert client.get(f"/api/import/{first}?lang=fr").json()["import_id"] == first
    assert client.get(f"/api/import/{second}").json()["import_id"] == second
    assert client.app.state.dataset_store.get(first) is None
    assert client.app.state.dataset_store.get(second) is not None

    third = post(client, ZIP_NAME, factories.build_zip()).json()["import_id"]
    assert client.get(f"/api/import/{first}").status_code == 404
    assert client.get(f"/api/import/{second}").status_code == 200
    assert client.get(f"/api/import/{third}").status_code == 200


def test_client_file_name_cannot_escape_the_workspace(client) -> None:
    body = post(client, "../../evil.zip", factories.build_zip()).json()

    assert body["file_name"] == "evil.zip"


def defective_zip() -> bytes:
    files = factories.default_files()
    files["reports/FilingIndicators.csv"] = files["reports/FilingIndicators.csv"].replace(
        b"B_99.01,true\n", b""
    )
    return factories.build_zip(files)


def test_import_in_french(client) -> None:
    response = client.post("/api/import?lang=fr", files={"file": (ZIP_NAME, defective_zip())})
    body = response.json()

    assert body["language"] == "fr"
    assert body["status"] == "FAILED", "codes and statuses are not translated"
    assert body["steps"][0]["name"] == "Détection du type de fichier"
    finding = body["messages"][0]
    assert finding["code"] == "PKG-011" and finding["severity"] == "BLOCKER"
    assert finding["message"] == (
        "Le tableau B_99.01 n'est pas déclaré dans la liste des tableaux remis "
        "(FilingIndicators.csv)."
    )
    assert "B_99.01,true" in finding["recommendation"]
    assert finding["expert_advice"].startswith("Ce fichier est souvent copié")
    assert finding["reference"]["text"].startswith("EBA, ")


def test_language_comes_from_the_browser_header_unless_chosen(client) -> None:
    headers = {"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
    files = {"file": (ZIP_NAME, factories.build_zip())}

    from_header = client.post("/api/import", files=files, headers=headers).json()
    chosen = client.post("/api/import?lang=en", files=files, headers=headers).json()
    unknown = client.post("/api/import?lang=de", files=files).json()

    assert (from_header["language"], chosen["language"], unknown["language"]) == ("fr", "en", "en")


def test_last_import_can_be_displayed_in_another_language_without_importing_again(client) -> None:
    english = post(client, ZIP_NAME, defective_zip()).json()

    french = client.get(f"/api/import/{english['import_id']}?lang=fr").json()

    assert french["import_id"] == english["import_id"]
    assert (english["language"], french["language"]) == ("en", "fr")
    assert english["messages"][0]["message"].startswith("Template B_99.01 is not declared")
    assert french["messages"][0]["message"].startswith("Le tableau B_99.01 n'est pas déclaré")
    assert french["counts"] == english["counts"]
    assert client.get("/api/import/unknown?lang=fr").json()["detail"].startswith("Import inconnu")


def test_supported_languages_are_listed(client) -> None:
    assert client.get("/api/languages").json() == ["en", "fr"]


def test_check_report_of_a_clean_zip_and_a_clean_envelope(client) -> None:
    zip_body = post(client, ZIP_NAME, factories.build_zip()).json()
    xml_body = post(client, "delivery.xml", factories.build_envelope()).json()

    assert zip_body["summary"]["score"] == 100
    assert zip_body["summary"]["failed"] == 0
    assert zip_body["summary"]["rows_analysed"] == 4
    # The envelope checks only apply to an XML delivery.
    assert xml_body["summary"]["checks_performed"] > zip_body["summary"]["checks_performed"]
    statuses = {c["id"]: c["status"] for c in zip_body["checks"]}
    assert statuses["env_root"] == "SKIPPED"
    assert statuses["pkg_templates"] == "PASSED"


def test_check_report_links_findings_to_checks(client) -> None:
    files = factories.default_files()
    files["reports/FilingIndicators.csv"] = files["reports/FilingIndicators.csv"].replace(
        b"B_02.01,true\n", b""
    )
    body = post(client, ZIP_NAME, factories.build_zip(files)).json()

    failed = {c["id"] for c in body["checks"] if c["status"] == "FAILED"}
    assert "pkg_indicator_lines" in failed
    assert {m["check_id"] for m in body["messages"]} <= {c["id"] for c in body["checks"]}
    assert body["summary"]["score"] < 100
    assert {c["key"] for c in body["categories"]} >= {"file", "structure"}


def test_technical_findings_come_with_a_location_and_the_data_check(client) -> None:
    files = factories.default_files()
    files["reports/b_03.01.csv"] = factories.table_csv(
        "B_03.01", {"c0010": "NO-SUCH-CONTRACT", "c0020": factories.LEI}
    )
    body = post(client, ZIP_NAME, factories.build_zip(files)).json()

    finding = next(m for m in body["messages"] if m["code"] == "DAT-005")
    assert finding["details"] == "#1 · NO-SUCH-CONTRACT"
    assert finding["check_id"] == "data_foreign_keys"
    assert finding["official_codes"] == ["EBA.807"]
    statuses = {c["id"]: c["status"] for c in body["checks"]}
    assert statuses["data_foreign_keys"] == "FAILED"
    assert statuses["data_primary_keys"] == "PASSED"
    assert body["status"] == "FAILED"
    assert body["steps"][-1] == {
        "key": "technical_rules",
        "name": "Technical rules",
        "status": "FAILED",
    }


def test_provisional_severity_is_flagged_and_identifier_findings_are_located(client) -> None:
    files = factories.default_files()
    files["reports/b_05.01.csv"] = factories.table_csv(
        "B_05.01",
        {"c0010": "5493001KJTIIGC8Y1R13", "c0020": "eba_qCO:qx2000"},
        {"c0010": "116737", "c0020": "eba_qCO:qx2002"},
    )
    body = post(client, ZIP_NAME, factories.build_zip(files)).json()
    by_code = {m["code"]: m for m in body["messages"]}

    assert by_code["DAT-010"]["severity"] == "MAJOR"
    assert by_code["DAT-010"]["severity_status"] == "PROVISIONAL"
    assert by_code["DAT-010"]["details"] == "#1 · '5493001KJTIIGC8Y1R13'"
    assert by_code["DAT-010"]["reference"]["type"] == "regulatory"
    assert by_code["DAT-011"]["check_id"] == "data_euid_syntax"
    statuses = {c["id"]: c["status"] for c in body["checks"]}
    assert statuses["data_lei_checksum"] == "WARNING"
    assert statuses["data_lei_format"] == "PASSED"
    assert body["status"] == "SUCCESS_WITH_WARNINGS"


def test_onegate_rules_apply_only_when_the_authority_is_the_acpr(client) -> None:
    """PO decision (#14): ENV-005 and ENV-006 are raised only for a register sent to the ACPR."""
    acpr = post(client, "delivery.xml", factories.build_envelope(recipient="XXX")).json()

    files = factories.default_files()
    files["reports/b_01.01.csv"] = files["reports/b_01.01.csv"].replace(b"ACPR", b"AMF")
    amf = post(
        client, "delivery.xml", factories.build_envelope(factories.build_zip(files), domain="ABC")
    ).json()

    assert [m["code"] for m in _unexpected(acpr)] == ["ENV-005"]
    assert next(s for s in acpr["steps"] if s["key"] == "extraction")["status"] == "WARNING"
    assert _unexpected(amf) == [] and amf["status"] == "SUCCESS"


def _unexpected(body: dict) -> list[dict]:
    """Findings of an answer, without those expected on the minimal synthetic package."""
    return [m for m in body["messages"] if m["code"] not in factories.SYNTHETIC_ADMITTED]
