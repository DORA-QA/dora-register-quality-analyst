# SPDX-License-Identifier: EUPL-1.2
"""Temporary folders of the imports.

Files exist on disk only while an import is being processed: each import gets
its own folder, removed as soon as the import ends. Leftovers of a crashed
process are removed when the API starts and stops.
"""

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

PREFIX = "roi-import-"


def _parent(temp_dir: str | None) -> Path:
    return Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())


@contextmanager
def import_workspace(temp_dir: str | None = None) -> Iterator[Path]:
    """Create the folder of one import and always delete it afterwards."""
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=_parent(temp_dir)))
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def purge_workspaces(temp_dir: str | None = None) -> int:
    """Delete every import folder left behind. Returns how many were removed."""
    removed = 0
    for folder in _parent(temp_dir).glob(f"{PREFIX}*"):
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
            removed += 1
    return removed
