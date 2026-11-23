# SPDX-License-Identifier: EUPL-1.2
"""Memory of large registers (load test of 30/10/2026, 3.5 million rows, 2 GB container)."""

import polars as pl
from fastapi.testclient import TestClient

from api.main import app
from api.services import import_service
from contracts import tables
from tests import factories
from tests.factories import CLIENT_HEADERS


def test_equal_values_of_a_column_share_one_object():
    frame = pl.DataFrame({"c0010": ["eba_GA:" + "FR" for _ in range(1000)], "_row": range(1000)})
    values = tables.column_values(frame, "c0010")
    assert values == ["eba_GA:FR"] * 1000
    assert len({id(value) for value in values}) == 1


def test_columns_read_by_the_rules_are_forgotten_after_the_import():
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        response = client.post("/api/import", files={"file": ("x.zip", factories.build_zip())})
    assert response.status_code == 200
    assert tables._COLUMNS == {}


def test_the_previous_register_is_released_before_the_next_one_is_read(monkeypatch):
    seen: list[object] = []

    def spy(self, file_path, file_name):
        seen.append(self._store.get(self._store_id_for_test))
        raise RuntimeError("stop")

    with TestClient(app, headers=CLIENT_HEADERS, raise_server_exceptions=False) as client:
        body = client.post("/api/import", files={"file": ("x.zip", factories.build_zip())}).json()
        service = app.state.import_service
        previous = body["import_id"]
        assert service._store.get(previous) is not None
        monkeypatch.setattr(service, "_store_id_for_test", previous, raising=False)
        monkeypatch.setattr(import_service.ImportService, "_run", spy)
        client.post("/api/import", files={"file": ("x.zip", factories.build_zip())})
        # Since 0.8.3 (RT-13) the findings of the previous analysis stay readable; the register
        # itself is still released before the next one is read.
        assert service.last_outcome(previous) is not None
    assert seen == [None]
