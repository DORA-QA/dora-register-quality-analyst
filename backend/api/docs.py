# SPDX-License-Identifier: EUPL-1.2
"""Offline API documentation.

By default FastAPI loads Swagger UI from a public CDN. The product must work
without internet access and must not call any external service, so Swagger UI
is served from files shipped with the API (``api/static/swagger-ui``).

ReDoc is disabled: it also relies on a CDN and adds nothing over Swagger UI.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

DOCS_URL = "/docs"
STATIC_URL = "/static"
STATIC_DIR = Path(__file__).resolve().parent / "static"
SWAGGER_UI_URL = f"{STATIC_URL}/swagger-ui"


def setup_offline_docs(app: FastAPI) -> None:
    """Serve Swagger UI on ``/docs`` using only local files.

    The application must be created with ``docs_url=None`` and
    ``redoc_url=None`` so that FastAPI does not register its CDN-based pages.
    """
    app.mount(STATIC_URL, StaticFiles(directory=STATIC_DIR), name="static")

    @app.get(DOCS_URL, include_in_schema=False)
    def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{app.title} - Swagger UI",
            swagger_js_url=f"{SWAGGER_UI_URL}/swagger-ui-bundle.js",
            swagger_css_url=f"{SWAGGER_UI_URL}/swagger-ui.css",
            swagger_favicon_url=f"{SWAGGER_UI_URL}/favicon-32x32.png",
            # No call to the online Swagger validator, whatever the host name.
            swagger_ui_parameters={"validatorUrl": None},
        )
