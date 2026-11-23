# SPDX-License-Identifier: EUPL-1.2
"""Confidentiality locks on the Docker deployment.

These tests fail if someone gives the backend a route to the internet or removes
the restrictions of the page. They protect the main promise of the product:
no data leaves the machine.
"""

import re
from pathlib import Path

import pytest
import yaml

from tests.factories import CLIENT_HEADERS

ROOT = Path(__file__).resolve().parents[2]


def _compose() -> dict:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_backend_is_only_on_an_internal_network() -> None:
    compose = _compose()
    backend = compose["services"]["backend"]

    networks = backend.get("networks")
    assert networks, "the backend must be attached to an explicit internal network"
    for name in networks:
        assert compose["networks"][name].get("internal") is True, f"{name} must be internal"
    assert "default" not in networks
    assert "ports" not in backend, "the backend must not publish ports (internal network)"
    assert backend.get("network_mode") is None


def test_backend_tmp_is_in_memory_only() -> None:
    tmpfs = _compose()["services"]["backend"].get("tmpfs", [])
    assert any(str(entry).split(":")[0] == "/tmp" for entry in tmpfs), "/tmp must be a tmpfs"


def test_published_ports_are_bound_to_localhost() -> None:
    for service in _compose()["services"].values():
        for port in service.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), port


def test_frontend_reaches_the_backend_through_the_internal_network() -> None:
    frontend = _compose()["services"]["frontend"]
    assert "internal" in frontend["networks"]


def _csp() -> str:
    conf = (ROOT / "docker" / "nginx.conf").read_text(encoding="utf-8")
    match = re.search(r'default "([^"]*)"', conf)
    assert match, "the Content-Security-Policy must be defined in nginx.conf"
    return match.group(1)


def test_csp_is_applied_by_nginx() -> None:
    conf = (ROOT / "docker" / "nginx.conf").read_text(encoding="utf-8")
    assert "add_header Content-Security-Policy $roi_csp always;" in conf


def test_csp_restricts_connections_to_localhost() -> None:
    directives = dict(
        part.strip().split(" ", 1) for part in _csp().split(";") if " " in part.strip()
    )
    sources = directives["connect-src"].split()
    allowed = {"'self'", "http://localhost:8000", "http://127.0.0.1:8000"}
    assert set(sources) <= allowed, f"unexpected connect-src: {sources}"
    assert directives["default-src"] == "'self'"
    assert "'unsafe-eval'" not in directives["script-src"]
    assert not re.search(r"https?://(?!localhost|127\.0\.0\.1)", _csp())


# ------------------------------------------------------------------ review S5: host names
LOCAL_NAMES = {"localhost", "127.0.0.1"}


def _servers() -> list[str]:
    conf = (ROOT / "docker" / "nginx.conf").read_text(encoding="utf-8")
    return re.findall(r"server \{(.*?)\n\}", conf, re.S)


def test_nginx_answers_only_the_names_of_this_machine() -> None:
    """DNS rebinding: any other Host gets no answer (444) on both ports."""
    servers = _servers()
    for port in ("3000", "8000"):
        defaults = [s for s in servers if re.search(rf"listen {port} default_server;", s)]
        assert len(defaults) == 1 and "return 444;" in defaults[0], port
        named = [s for s in servers if re.search(rf"listen {port};", s)]
        assert len(named) == 1, port
        names = set(re.search(r"server_name ([^;]+);", named[0]).group(1).split())
        assert names == LOCAL_NAMES, (port, names)


def test_api_accepts_only_the_three_local_host_names() -> None:
    from api.config import Settings

    assert Settings.model_fields["allowed_hosts"].default == ["localhost", "127.0.0.1", "backend"]


def test_api_refuses_another_host_name() -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app, headers=CLIENT_HEADERS) as client:
        assert client.get("/health", headers={"Host": "attacker.example"}).status_code == 400
        assert client.get("/health", headers={"Host": "localhost:8000"}).status_code == 200
        assert client.get("/health", headers={"Host": "127.0.0.1:8000"}).status_code == 200
        assert client.get("/health", headers={"Host": "backend:8000"}).status_code == 200


# ------------------------------------------------------------------ review S7: hardening
@pytest.mark.parametrize("service", ["backend", "frontend"])
def test_containers_are_hardened(service: str) -> None:
    """Read-only, no capability, no privilege gain, memory and process limits."""
    config = _compose()["services"][service]
    assert config.get("read_only") is True
    assert config.get("cap_drop") == ["ALL"]
    assert "no-new-privileges:true" in config.get("security_opt", [])
    assert config.get("mem_limit")
    assert config.get("pids_limit")
    # A read-only container still needs a place to write: in memory only.
    assert any(str(entry).split(":")[0] == "/tmp" for entry in config.get("tmpfs", []))


def test_frontend_image_runs_nginx_without_root() -> None:
    dockerfile = (ROOT / "docker" / "frontend.Dockerfile").read_text(encoding="utf-8")
    final_stage = dockerfile.rsplit("FROM ", 1)[1]
    assert final_stage.startswith("nginxinc/nginx-unprivileged:")


def test_backend_image_runs_without_root_and_without_tests() -> None:
    dockerfile = (ROOT / "docker" / "backend.Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^USER (?!root)\w+", dockerfile, re.M)
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert {"backend/tests", "backend/tools"} <= set(ignored)


def test_base_images_are_pinned_by_digest() -> None:
    """Review S7: a tag can be moved; a digest names one exact image (Dependabot updates it)."""
    for name in ("backend.Dockerfile", "frontend.Dockerfile"):
        dockerfile = (ROOT / "docker" / name).read_text(encoding="utf-8")
        for image in re.findall(r"^FROM (\S+)", dockerfile, re.M):
            assert re.search(r"@sha256:[0-9a-f]{64}$", image), f"{name}: {image}"
