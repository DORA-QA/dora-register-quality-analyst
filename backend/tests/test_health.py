# SPDX-License-Identifier: EUPL-1.2
"""Tests of the health endpoint."""

from api.config import APP_VERSION


def test_health_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_returns_version(client) -> None:
    response = client.get("/health")

    assert response.json() == {"status": "ok", "version": APP_VERSION, "taxonomy_version": "4.0"}


def test_frontend_and_backend_carry_the_same_version() -> None:
    """CL-41: the interface showed 0.7 while the API was in 0.8.4."""
    import json
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    frontend = json.loads((root / "frontend" / "package.json").read_text("utf-8"))["version"]
    backend = tomllib.loads((root / "backend" / "pyproject.toml").read_text("utf-8"))["project"][
        "version"
    ]
    assert frontend == backend == APP_VERSION


def test_cors_allows_local_frontend(client) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_about_gives_the_engine_and_its_sources(client) -> None:
    """Brief of Sprint 4, §22 and §23: one source for the version, sources traceable."""
    about = client.get("/about").json()

    assert about["version"] == APP_VERSION
    assert about["taxonomy_version"] == "4.0"
    assert about["catalog_codes"] > 100
    assert len(about["catalog_fingerprint"]) == 12
    assert about["legal_notice"] is None and about["licence"] is None
    ids = [source["id"] for source in about["sources"]]
    assert ids[:2] == ["dora", "its"]
    assert {"eba_codes", "eba_labels", "eba_rules", "eba_deactivations"} <= set(ids)
    for source in about["sources"]:
        assert source["url"].startswith("https://")
        if source["id"].startswith("eba_"):
            assert len(source["sha256"]) == 64 and source["published"]
