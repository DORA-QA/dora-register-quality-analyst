# SPDX-License-Identifier: EUPL-1.2
"""Contract of the health endpoint."""

from typing import Literal

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Status returned by ``GET /health``."""

    status: Literal["ok"]
    version: str
    # Since 0.8.4 (CL-41): EBA taxonomy the engine checks against.
    taxonomy_version: str | None = None


class GleifStatusResponse(BaseModel):
    """Status returned by ``GET /api/gleif/status`` (branch feature/gleif-local)."""

    # UPDATING: the copy is being downloaded, no register is accepted. READY, UNAVAILABLE, DISABLED.
    state: Literal["UPDATING", "READY", "UNAVAILABLE", "DISABLED"]
    release: str | None = None
    # Date and time of the GLEIF publication of the installed copy (UTC).
    content_date: str | None = None
    received_bytes: int = 0
    total_bytes: int = 0
    last_error: str | None = None
