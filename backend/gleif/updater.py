# SPDX-License-Identifier: EUPL-1.2
"""Downloads the latest GLEIF copy published on GitHub, then exits (online version only).

Run at start-up, before any register is accepted, in a process of its own that never sees a
register: by the portable launcher (``DORA-QA --gleif-update``) or by the ``gleif-updater``
container of the Docker stack (``python -m gleif.updater``). The analysis only reads the copy.

Strict rule "never online during an analysis" (decision A9, issue PO-38 point 1):

- a heartbeat thread rewrites ``status.json`` every 2 s while this process runs, even when a read
  is blocked, so the API keeps refusing registers as long as the process is alive;
- every network operation times out after ``TIMEOUT_SECONDS`` and the whole update after
  ``MAX_SECONDS``; the launcher also kills the process if it outlives that limit.

Source: the public releases of the data repository whose tag starts with ``gleif-`` (built by
``tools/build_gleif.py``). Each release holds ``manifest.json`` (date of the GLEIF publication,
SHA-256 of each file) and the Parquet files. No token is needed.

Environment:
    ROI_GLEIF_DIR          folder of the copy (default /data/gleif)
    ROI_GLEIF_REPO         owner/name of the data repository (default: ``DEFAULT_REPO``)
    ROI_GLEIF_TAG_PREFIX   prefix of the release tags (default gleif-)
    ROI_GLEIF_TOKEN        optional GitHub token (higher rate limit, private test repository)
    ROI_GLEIF_API          GitHub API (default https://api.github.com)
    ROI_GLEIF_HOLD_SECONDS acceptance tests only: keep the state UPDATING this many seconds before
                           starting (default 0), so that the waiting screen can be checked even
                           when the download is faster than the start of the page

Never fails the container: on error, the installed copy (if any) is kept and the reason is written
in ``status.json`` (``last_error``).
"""

import hashlib
import json
import logging
import os
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from http.client import HTTPResponse
from pathlib import Path
from typing import cast

from contracts.gleif import GleifState
from contracts.json_types import JsonDict
from gleif.layout import (
    CURRENT,
    DATA_FILES,
    MANIFEST,
    MANIFEST_FORMAT,
    STATUS,
    installed_manifest,
    read_json,
    root_dir,
)
from gleif.status import write_status

logger = logging.getLogger("roi.gleif.updater")
DEFAULT_REPO = "DORA-QA/dora-qa-gleif-data"
DEFAULT_PREFIX = "gleif-"
DEFAULT_API = "https://api.github.com"
# Each network operation: well under the heartbeat timeout of the API (gleif.status, 60 s).
TIMEOUT_SECONDS = 20
# Whole update: beyond, the update gives up and the tool starts with the installed copy, if any.
MAX_SECONDS = 900
CHUNK = 1 << 20
HEARTBEAT_SECONDS = 2.0


class UpdateError(Exception):
    """A failed update; ``reason`` is written in status.json (no secret, no URL with a token)."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


class GitHubReleases:
    def __init__(self, repo: str, token: str | None, api: str = DEFAULT_API) -> None:
        self._repo = repo
        self._token = token
        self._api = api.rstrip("/")

    def _request(self, url: str, accept: str) -> urllib.request.Request:
        request = urllib.request.Request(url, headers={"Accept": accept})
        request.add_header("User-Agent", "dora-qa-gleif-updater")
        if self._token:
            # Not forwarded on redirect (the asset is served from a signed storage URL).
            request.add_unredirected_header("Authorization", f"Bearer {self._token}")
        return request

    def latest(self, prefix: str) -> JsonDict:
        url = f"{self._api}/repos/{self._repo}/releases?per_page=50"
        try:
            with urllib.request.urlopen(
                self._request(url, "application/vnd.github+json"), timeout=TIMEOUT_SECONDS
            ) as response:
                releases: list[JsonDict] = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 404):
                # A private repository answers 404 without a valid token.
                raise UpdateError("no_access", str(error.code)) from None
            raise UpdateError("github_error", str(error.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise UpdateError("network", type(error).__name__) from None
        candidates = [
            r
            for r in releases
            if str(r.get("tag_name", "")).startswith(prefix)
            and not r.get("draft")
            and not r.get("prerelease")
        ]
        if not candidates:
            raise UpdateError("no_release")
        return max(candidates, key=lambda r: str(r.get("published_at") or ""))

    def open_asset(self, asset: JsonDict) -> HTTPResponse:
        try:
            response = urllib.request.urlopen(
                self._request(str(asset["url"]), "application/octet-stream"),
                timeout=TIMEOUT_SECONDS,
            )
        except urllib.error.HTTPError as error:
            raise UpdateError("download_error", str(error.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise UpdateError("network", type(error).__name__) from None
        return cast(HTTPResponse, response)


def _assets(release: JsonDict) -> dict[str, JsonDict]:
    return {str(a["name"]): a for a in release.get("assets", [])}


class _Progress:
    def __init__(self, root: Path, total: int) -> None:
        self.root, self.total, self.received, self._last = root, total, 0, 0.0
        self.deadline = time.monotonic() + MAX_SECONDS

    def add(self, size: int) -> None:
        self.received += size
        if time.monotonic() > self.deadline:
            raise UpdateError("too_long", f"over {MAX_SECONDS} s")
        if time.monotonic() - self._last >= HEARTBEAT_SECONDS:
            self.beat()

    def beat(self) -> None:
        self._last = time.monotonic()
        write_status(
            self.root,
            GleifState.UPDATING,
            received_bytes=self.received,
            total_bytes=self.total,
        )


def _download(
    source: GitHubReleases, asset: JsonDict, target: Path, expected: JsonDict, progress: _Progress
) -> None:
    digest = hashlib.sha256()
    with source.open_asset(asset) as response, target.open("wb") as out:
        while chunk := response.read(CHUNK):
            out.write(chunk)
            digest.update(chunk)
            progress.add(len(chunk))
    if digest.hexdigest() != expected.get("sha256"):
        raise UpdateError("checksum", target.name)


def update(root: Path, source: GitHubReleases, prefix: str = DEFAULT_PREFIX) -> str:
    """Install the latest release if it differs from the installed one. Returns its tag."""
    root.mkdir(parents=True, exist_ok=True)
    progress = _Progress(root, 0)
    progress.beat()
    release = source.latest(prefix)
    tag = str(release["tag_name"])
    assets = _assets(release)
    if MANIFEST not in assets:
        raise UpdateError("bad_release", "manifest.json missing")
    with source.open_asset(assets[MANIFEST]) as response:
        manifest: JsonDict = json.load(response)
    files = manifest.get("files", {})
    if manifest.get("format") != MANIFEST_FORMAT or not all(n in files for n in DATA_FILES):
        raise UpdateError("bad_release", "unexpected manifest")
    if any(name not in assets for name in DATA_FILES):
        raise UpdateError("bad_release", "data file missing")

    installed = installed_manifest(root)
    if installed and installed.get("files") == files:
        logger.info("GLEIF copy %s already installed", tag)
        return tag

    incoming = root / f".incoming-{os.getpid()}"
    shutil.rmtree(incoming, ignore_errors=True)
    incoming.mkdir()
    progress.total = sum(int(files[n].get("bytes", 0)) for n in DATA_FILES)
    try:
        for name in DATA_FILES:
            _download(source, assets[name], incoming / name, files[name], progress)
        manifest["release"] = tag
        (incoming / MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        _swap(root, incoming)
    finally:
        shutil.rmtree(incoming, ignore_errors=True)
    logger.info("GLEIF copy %s installed (%s)", tag, manifest.get("content_date"))
    return tag


def _swap(root: Path, incoming: Path) -> None:
    current = root / CURRENT
    previous = root / ".previous"
    shutil.rmtree(previous, ignore_errors=True)
    if current.exists():
        os.replace(current, previous)
    os.replace(incoming, current)
    shutil.rmtree(previous, ignore_errors=True)


def _clean_leftovers(root: Path) -> None:
    for leftover in root.glob(".incoming-*"):
        shutil.rmtree(leftover, ignore_errors=True)


def hold(root: Path, seconds: float) -> None:
    """Keep the state UPDATING (heartbeat included) for ``seconds``: acceptance tests only."""
    end = time.monotonic() + seconds
    while (left := end - time.monotonic()) > 0:
        write_status(root, GleifState.UPDATING, received_bytes=0, total_bytes=0)
        time.sleep(min(HEARTBEAT_SECONDS, left))


class Heartbeat:
    """Writes UPDATING every ``HEARTBEAT_SECONDS`` while the update runs, whatever it waits for."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="gleif-heartbeat")

    def _run(self) -> None:
        while not self._stop.wait(HEARTBEAT_SECONDS):
            current = read_json(self._root / STATUS) or {}
            write_status(
                self._root,
                GleifState.UPDATING,
                received_bytes=int(current.get("received_bytes", 0) or 0),
                total_bytes=int(current.get("total_bytes", 0) or 0),
            )

    def __enter__(self) -> "Heartbeat":
        write_status(self._root, GleifState.UPDATING, received_bytes=0, total_bytes=0)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        self._thread.join()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    root = root_dir()
    root.mkdir(parents=True, exist_ok=True)
    _clean_leftovers(root)
    try:
        held = float(os.environ.get("ROI_GLEIF_HOLD_SECONDS", "0") or 0)
    except ValueError:
        held = 0.0
    if held > 0:
        logger.info("Acceptance mode: state kept on UPDATING for %.0f s", held)
        hold(root, min(held, 600.0))
    source = GitHubReleases(
        os.environ.get("ROI_GLEIF_REPO", DEFAULT_REPO),
        os.environ.get("ROI_GLEIF_TOKEN") or None,
        os.environ.get("ROI_GLEIF_API", DEFAULT_API),
    )
    prefix = os.environ.get("ROI_GLEIF_TAG_PREFIX", DEFAULT_PREFIX)
    try:
        with Heartbeat(root):
            update(root, source, prefix)
        error = None
    except UpdateError as failure:
        logger.warning("GLEIF update failed: %s", failure)
        error = failure.reason
    except Exception as failure:  # noqa: BLE001 - never leave the status on UPDATING
        logger.error("GLEIF update failed: %s", type(failure).__name__)
        error = "internal"
    state = GleifState.READY if installed_manifest(root) else GleifState.UNAVAILABLE
    write_status(root, state, last_error=error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
