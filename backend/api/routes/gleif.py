# SPDX-License-Identifier: EUPL-1.2
"""State of the local GLEIF copy (branch feature/gleif-local).

The page polls this endpoint at start-up: while the copy is being updated it shows a waiting
screen and the import endpoint answers 503.
"""

import time
from pathlib import Path

from fastapi import APIRouter, Request

from api.config import get_settings
from contracts.health import GleifStatusResponse
from gleif.status import GleifStatus, read_status

router = APIRouter(prefix="/api", tags=["gleif"])


def current_status(request: Request) -> GleifStatus:
    settings = get_settings()
    started = getattr(request.app.state, "started_epoch", time.time())
    return read_status(
        Path(settings.gleif_dir), enabled=settings.gleif_enabled, started_epoch=started
    )


@router.get("/gleif/status", summary="State of the local GLEIF copy")
def get_gleif_status(request: Request) -> GleifStatusResponse:
    found = current_status(request)
    return GleifStatusResponse(
        state=found.state.value,
        release=found.release,
        content_date=found.content_date,
        received_bytes=found.received_bytes,
        total_bytes=found.total_bytes,
        last_error=found.last_error,
    )
