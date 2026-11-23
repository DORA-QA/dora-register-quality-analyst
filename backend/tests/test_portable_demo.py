# SPDX-License-Identifier: EUPL-1.2
"""Single-process mode of the portable demo build (api/portable.py)."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.portable import setup_portable_frontend


def make_client(tmp_path: Path) -> TestClient:
    (tmp_path / "index.html").write_text("<html>DEMO</html>", encoding="utf-8")
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    setup_portable_frontend(app, str(tmp_path))
    return TestClient(app)


def test_interface_is_served_with_security_headers(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/")
    assert response.status_code == 200
    assert "DEMO" in response.text
    assert "connect-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_api_routes_keep_priority_over_files(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/health")
    assert response.json() == {"status": "ok"}
    assert "content-security-policy" not in response.headers


def test_missing_build_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="index.html"):
        setup_portable_frontend(FastAPI(), str(tmp_path))
