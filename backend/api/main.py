# SPDX-License-Identifier: EUPL-1.2
"""FastAPI application entry point.

Run locally with::

    uv run uvicorn api.main:app --reload
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from api.config import APP_NAME, APP_VERSION, get_settings
from api.docs import setup_offline_docs
from api.portable import setup_portable_frontend
from api.routes import about, gleif, health, imports
from api.services.import_service import ImportService
from api.services.workspace import purge_workspaces
from dataset.store import DatasetStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Nothing survives a restart: temporary files and the dataset are dropped."""
    settings = get_settings()
    app.state.started_epoch = time.time()
    purge_workspaces(settings.temp_dir)
    store = DatasetStore(ttl_seconds=settings.dataset_ttl_minutes * 60)
    app.state.dataset_store = store
    service = ImportService(settings, store)
    app.state.import_service = service
    sweeper = asyncio.create_task(_expire_periodically(service))
    try:
        yield
    finally:
        sweeper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweeper
        service.forget()
        purge_workspaces(settings.temp_dir)


EXPIRY_SWEEP_SECONDS = 60


async def _expire_periodically(service: ImportService) -> None:
    """Drop the register and its findings after inactivity, even if nobody reads them."""
    while True:
        await asyncio.sleep(EXPIRY_SWEEP_SECONDS)
        service.expire()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="Quality assurance engine for DORA Registers of Information.",
        # The default documentation pages load their assets from a public CDN.
        # They are replaced by an offline Swagger UI (see api/docs.py).
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Only the names of this machine (review S5): a page whose domain resolves to 127.0.0.1
    # (DNS rebinding) is answered 400. The port is ignored.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(about.router)
    app.include_router(imports.router)
    app.include_router(gleif.router)
    setup_offline_docs(app)
    if settings.static_dir:
        setup_portable_frontend(app, settings.static_dir)

    return app


app = create_app()
