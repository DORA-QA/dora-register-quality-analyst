# SPDX-License-Identifier: EUPL-1.2
"""Single-process mode of the portable build (api/portable.py)."""

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


def test_page_is_never_taken_from_an_older_cache(tmp_path: Path) -> None:
    # The same address (127.0.0.1:8765) serves every version of DORA QA: a cached page of an
    # older version would hide the newer interface.
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.js").write_text("x", encoding="utf-8")
    client = make_client(tmp_path)
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/index.html").headers["cache-control"] == "no-cache"
    assert "immutable" in client.get("/assets/index-abc123.js").headers["cache-control"]
    assert client.get("/health").headers["cache-control"] == "no-store"


def test_missing_build_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="index.html"):
        setup_portable_frontend(FastAPI(), str(tmp_path))


def test_the_sources_variant_ships_every_backend_package_of_the_zip() -> None:
    """build_sources.py and build.py must list the same backend packages (gleif was missing)."""
    import ast
    from pathlib import Path

    portable = Path(__file__).resolve().parents[2] / "portable"
    sources = ast.parse((portable / "build_sources.py").read_text(encoding="utf-8"))
    parts = next(
        node.value
        for node in ast.walk(sources)
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "BACKEND_PARTS"
    )
    shipped = {element.value for element in parts.elts}  # type: ignore[attr-defined]
    frozen = (portable / "build.py").read_text(encoding="utf-8")
    backend = Path(__file__).resolve().parents[1]
    packages = {p.name for p in backend.iterdir() if (p / "__init__.py").is_file()}
    needed = {name for name in packages - {"tests", "tools"} if f'"{name}"' in frozen}
    assert needed <= shipped, needed - shipped
