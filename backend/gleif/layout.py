# SPDX-License-Identifier: EUPL-1.2
"""Files of the local copy, shared by the updater (writer) and the backend (reader).

    <root>/status.json          state of the copy, rewritten by the updater (heartbeat)
    <root>/current/manifest.json
    <root>/current/lei.parquet   one row per LEI
    <root>/current/rr.parquet    one row per relationship (child, parent, type, status)

``current`` is replaced in one rename, so a reader never sees half a copy.
"""

import json
import os
from pathlib import Path

from contracts.json_types import JsonDict

DEFAULT_ROOT = "/data/gleif"
MANIFEST = "manifest.json"
STATUS = "status.json"
CURRENT = "current"
DATA_FILES = ("lei.parquet", "rr.parquet")
MANIFEST_FORMAT = 1


def root_dir() -> Path:
    return Path(os.environ.get("ROI_GLEIF_DIR", DEFAULT_ROOT))


def current_dir(root: Path) -> Path:
    return root / CURRENT


def read_json(path: Path) -> JsonDict | None:
    """The JSON object of a file, or None if it is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_json_atomically(path: Path, data: JsonDict) -> None:
    """Write next to the target then rename: a reader sees the old or the new file, never half."""
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporary, path)


def installed_manifest(root: Path) -> JsonDict | None:
    """Manifest of the installed copy, if every data file it lists is present."""
    folder = current_dir(root)
    manifest = read_json(folder / MANIFEST)
    if manifest is None or manifest.get("format") != MANIFEST_FORMAT:
        return None
    if not all((folder / name).is_file() for name in DATA_FILES):
        return None
    return manifest
