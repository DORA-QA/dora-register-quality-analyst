# SPDX-License-Identifier: EUPL-1.2
"""State of the local copy, written by the updater and read by the API.

The updater rewrites ``status.json`` every few seconds while it works (heartbeat). The API reads
it to decide whether a register may be accepted:

- ``UPDATING`` while the heartbeat is fresh: the screen shows the update and imports are refused;
- otherwise ``READY`` if a complete copy is installed, else ``UNAVAILABLE`` (GLEIF checks are then
  "not evaluated", the rest of the analysis runs normally).

If the updater has not written anything yet, the API waits ``startup_wait`` seconds after its own
start (the two containers start together), then falls back on what is installed. A crashed updater
therefore never blocks the tool for more than ``heartbeat_timeout`` seconds.
"""

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from contracts.gleif import GleifState
from contracts.json_types import JsonDict
from gleif.layout import STATUS, installed_manifest, read_json, write_json_atomically

HEARTBEAT_TIMEOUT_SECONDS = 60
STARTUP_WAIT_SECONDS = 90


@dataclass(frozen=True)
class GleifStatus:
    state: GleifState
    # Release and GLEIF publication date of the installed copy (None if none).
    release: str | None = None
    content_date: str | None = None
    # While updating: bytes received and expected (0 when unknown).
    received_bytes: int = 0
    total_bytes: int = 0
    # Short machine-readable reason of the last failed update ("network", "no_access", ...);
    # "interrupted" when the updater stopped without saying why (crash, killed process).
    last_error: str | None = None


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_status(root: Path, state: GleifState, **fields: object) -> None:
    """Called by the updater (heartbeat included)."""
    data: JsonDict = {"state": state.value, "updated_at": now_iso(), "updated_epoch": time.time()}
    data.update(fields)
    write_json_atomically(root / STATUS, data)


def read_status(
    root: Path,
    *,
    enabled: bool = True,
    started_epoch: float | None = None,
    heartbeat_timeout: float = HEARTBEAT_TIMEOUT_SECONDS,
    startup_wait: float = STARTUP_WAIT_SECONDS,
    now: float | None = None,
) -> GleifStatus:
    if not enabled:
        return GleifStatus(GleifState.DISABLED)
    now = time.time() if now is None else now
    manifest = installed_manifest(root)
    release = str(manifest.get("release")) if manifest else None
    content_date = str(manifest.get("content_date")) if manifest else None
    written = read_json(root / STATUS)
    fallback = GleifState.READY if manifest else GleifState.UNAVAILABLE
    if written is None:
        waiting = started_epoch is not None and now - started_epoch < startup_wait
        return GleifStatus(
            GleifState.UPDATING if waiting else fallback,
            release=release,
            content_date=content_date,
        )
    last_error = written.get("last_error")
    error = str(last_error) if last_error else None
    if written.get("state") == GleifState.UPDATING.value:
        beat = float(written.get("updated_epoch", 0) or 0)
        if now - beat < heartbeat_timeout:
            return GleifStatus(
                GleifState.UPDATING,
                received_bytes=int(written.get("received_bytes", 0) or 0),
                total_bytes=int(written.get("total_bytes", 0) or 0),
                last_error=error,
                release=release,
                content_date=content_date,
            )
        # The updater died while working (no heartbeat): the update failed, say so.
        error = error or "interrupted"
    return GleifStatus(fallback, release=release, content_date=content_date, last_error=error)
