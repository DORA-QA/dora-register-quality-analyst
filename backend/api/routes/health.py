# SPDX-License-Identifier: EUPL-1.2
"""Health endpoint, used by the frontend and by Docker to check the API."""

from fastapi import APIRouter

from api.config import APP_VERSION
from contracts.data_model import DEFAULT_VERSION
from contracts.health import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", summary="API health check")
def get_health() -> HealthStatus:
    """Return the API status, version and the EBA taxonomy checked against."""
    return HealthStatus(status="ok", version=APP_VERSION, taxonomy_version=DEFAULT_VERSION)
