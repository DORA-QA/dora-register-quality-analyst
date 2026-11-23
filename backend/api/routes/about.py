# SPDX-License-Identifier: EUPL-1.2
"""« About the engine » endpoint: version, catalogue, taxonomy and sources (brief §22, §23)."""

from fastapi import APIRouter

from api.config import APP_VERSION
from contracts.about import AboutInfo, about

router = APIRouter(tags=["health"])


@router.get("/about", summary="Version, catalogue and sources of the engine")
def get_about() -> AboutInfo:
    """Same version as ``/health`` (one source); no register data."""
    return about(APP_VERSION)
