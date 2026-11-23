# SPDX-License-Identifier: EUPL-1.2
"""Tests of the offline API documentation.

Confidentiality rule: the product never calls an external service. These tests
fail if the documentation page references anything outside the API itself.
"""

import re

EXTERNAL_URL = re.compile(r"""(?:https?:)?//[^\s"'<>]+""")


def test_swagger_is_available(client) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text


def test_swagger_page_references_no_external_url(client) -> None:
    html = client.get("/docs").text

    assert EXTERNAL_URL.findall(html) == []


def test_swagger_assets_are_served_locally(client) -> None:
    html = client.get("/docs").text
    assets = re.findall(r"""(?:src|href)=["']([^"']+)["']""", html)

    assert assets, "the documentation page should reference its assets"
    for asset in assets:
        assert asset.startswith("/static/swagger-ui/")
        assert client.get(asset).status_code == 200


def test_redoc_is_disabled(client) -> None:
    assert client.get("/redoc").status_code == 404


def test_openapi_schema_is_available(client) -> None:
    schema = client.get("/openapi.json").json()

    assert "/health" in schema["paths"]
    assert "/docs" not in schema["paths"]
