# SPDX-License-Identifier: EUPL-1.2
"""Chaque mutation de cellule déclenche le code attendu, et seulement lui parmi les contrôles
de la famille (CL-18, phase 1). Les colonnes sans ligne dans le golden sont listées, pas ignorées.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.cases.cell_mutations import generate
from tests.factories import CLIENT_HEADERS

VARIANTS, MISSING = generate()


def test_every_missing_field_is_reported() -> None:
    assert MISSING, "les colonnes absentes du golden doivent être signalées"
    assert all("(" in item for item in MISSING)


@pytest.fixture(scope="module")
def client():
    with TestClient(app, headers=CLIENT_HEADERS) as c:
        yield c


@pytest.mark.parametrize("variant", VARIANTS, ids=lambda v: v.case)
def test_variant_raises_expected_code(client, variant) -> None:
    response = client.post("/api/import", files={"file": (variant.package_name, variant.content)})
    codes = [m["code"] for m in response.json().get("messages", [])]
    assert variant.code in codes, f"{variant.description} : attendu {variant.code}, obtenu {codes}"
