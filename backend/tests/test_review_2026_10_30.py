# SPDX-License-Identifier: EUPL-1.2
"""Corrections of the quality and security review of 30/10/2026 (docs/revue-2026-10-30.md)."""

import ast
import logging
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes.imports import MAX_NAME_BYTES, safe_file_name
from api.services import import_service
from contracts import identifiers
from tests import factories
from tests.factories import CLIENT_HEADERS

BACKEND = Path(__file__).resolve().parent.parent
GOLDEN = BACKEND / "tests" / "golden" / "golden.sample.zip"
FRENCH_LETTERS = re.compile(r"[éèêàâùûçôîï]")


def _post(client: TestClient, name: str, content: bytes, lang: str = "en"):
    return client.post(f"/api/import?lang={lang}", files={"file": (name, content)})


# ------------------------------------------------------------------ S1: no register value kept
def test_identifiers_of_the_register_are_not_kept_after_the_import():
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        assert _post(client, GOLDEN.name, GOLDEN.read_bytes()).status_code == 200
    for cached in (identifiers.analyse_lei, identifiers.analyse_euid, identifiers.recognised_kinds):
        assert cached.cache_info().currsize == 0, cached.__name__


# ------------------------------------------------------------------ S2: long file names
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("é" * 300 + ".zip", "upload.zip"),
        ("a" * 250 + ".zip", "upload.zip"),
        ("x" * 300 + "." + "y" * 50, "upload"),
        ("dir/../../package.zip", "package.zip"),
        ("..", "upload"),
        ("a\x00b.zip", "upload"),
        (None, "upload"),
    ],
)
def test_file_names_are_usable_on_disk(name, expected):
    found = safe_file_name(name)
    assert found == expected
    assert len(found.encode("utf-8")) <= MAX_NAME_BYTES


def test_a_very_long_file_name_is_not_an_internal_error():
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        response = _post(client, "é" * 300 + ".zip", factories.build_zip())
    assert response.status_code == 200


# ------------------------------------------------------------------ S3: no traceback text
def test_an_unexpected_failure_logs_its_type_only(monkeypatch, caplog):
    def explode(self, file_path, file_name):
        raise ValueError("valeur du registre : ACME SECRET")

    monkeypatch.setattr(import_service.ImportService, "_run", explode)
    with (
        TestClient(app, headers=CLIENT_HEADERS, raise_server_exceptions=False) as client,
        caplog.at_level(logging.DEBUG),
    ):
        response = _post(client, "x.zip", factories.build_zip(), lang="fr")
    assert response.status_code == 500
    assert "Erreur interne" in response.json()["detail"]
    assert "ACME SECRET" not in caplog.text
    assert "import failed: ValueError" in caplog.text


# ------------------------------------------------------------------ Q1, Q2: details
def _formatted_strings(path: Path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    yield node.lineno, part.value


def test_details_written_by_the_rules_hold_no_words_of_a_language():
    """Details are shown in every language: codes, values and symbols only (i18n contract)."""
    found = [
        f"{path.relative_to(BACKEND)}:{line} {text!r}"
        for folder in ("rules", "indicators")
        for path in (BACKEND / folder).rglob("*.py")
        for line, text in _formatted_strings(path)
        if FRENCH_LETTERS.search(text)
    ]
    assert not found, "\n".join(found)


def test_unused_provider_without_name_is_shown_without_none():
    """DQ-004: a provider without name used to be shown as 'None'."""
    files = factories.default_files()
    files["reports/b_05.01.csv"] += b"UNUSEDPROVIDER000001,eba_qCO:qx2003,,,,,,,,,,\n"
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        body = _post(client, "x.zip", factories.build_zip(files=files)).json()
    details = [m["details"] for m in body["messages"] if m["code"] == "DQ-004"]
    assert details and all("None" not in (d or "") for d in details)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("registre‮csv.zip", "registrecsv.zip"),
        ("a​b.zip", "ab.zip"),
        ("tab\there.zip", "tabhere.zip"),
        ("‮", "upload"),
    ],
)
def test_control_and_invisible_characters_are_dropped_from_the_file_name(name, expected):
    """Red team of 07/11 (RT-24, CL-47): a right-to-left override would disguise the name."""
    assert safe_file_name(name) == expected
