# SPDX-License-Identifier: EUPL-1.2
"""Reference data of the DORA module, organised by taxonomy version.

The data lives in ``reference/dora/versions.json``. Supporting a new version of
the taxonomy means adding an entry to that file, not changing the code.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import cast

from contracts.json_types import JsonDict

REFERENCE_FILE = Path(__file__).resolve().parent.parent / "reference" / "dora" / "versions.json"
ENTRY_POINT_VERSION = re.compile(r"/fws/dora/([0-9.]+)/mod/dora\.json$")


@dataclass(frozen=True)
class TaxonomyVersion:
    version: str
    module_code: str
    entry_points: tuple[str, ...]
    templates: tuple[str, ...]
    required_parameters: tuple[str, ...]
    optional_parameters: tuple[str, ...]


@lru_cache
def _load() -> JsonDict:
    return cast(JsonDict, json.loads(REFERENCE_FILE.read_text(encoding="utf-8")))


def supported_versions() -> list[str]:
    return sorted(_load()["versions"])


def default_version() -> TaxonomyVersion:
    version = get_version(_load()["default"])
    if version is None:
        raise RuntimeError("the default taxonomy version is not in the reference file")
    return version


def get_version(version: str) -> TaxonomyVersion | None:
    entry = _load()["versions"].get(version)
    if entry is None:
        return None
    return TaxonomyVersion(
        version=version,
        module_code=entry["module_code"],
        entry_points=tuple(entry["entry_points"]),
        templates=tuple(entry["templates"]),
        required_parameters=tuple(entry["parameters"]["required"]),
        optional_parameters=tuple(entry["parameters"]["optional"]),
    )


def version_from_entry_point(entry_point: str) -> str | None:
    """Read the taxonomy version in an entry point URL (``.../dora/4.0/mod/dora.json``)."""
    match = ENTRY_POINT_VERSION.search(entry_point)
    return match.group(1) if match else None
