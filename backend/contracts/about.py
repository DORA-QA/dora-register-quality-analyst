# SPDX-License-Identifier: EUPL-1.2
"""Contract of the « About the engine » endpoint (brief of Sprint 4, §22 and §23).

Everything comes from files already in the repository: the version, the catalogue and its
fingerprint, and the provenance of the reference files (URL, publication date, SHA-256). The
legal notice is the disclaimer of DORA QA (translated by the interface); the licence is EUPL 1.2.
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from contracts.check_report import catalog_fingerprint
from contracts.data_model import DEFAULT_VERSION
from contracts.disclaimer import DISCLAIMER, LICENCE
from contracts.messages import load_catalog

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "reference" / "dora"
PROVENANCE_FILES = (
    "enumerations-4.0.provenance.json",
    "rule-status-4.0.provenance.json",
)

# Legal texts the checks rely on (European Legislation Identifier, stable addresses).
LEGAL_TEXTS = (
    ("dora", "https://eur-lex.europa.eu/eli/reg/2022/2554/oj"),
    ("its", "https://eur-lex.europa.eu/eli/reg_impl/2024/2956/oj"),
)


class AboutSource(BaseModel):
    """A source of the checks. ``id`` is translated by the interface; ``title`` is the
    official title kept in the provenance file, when there is one."""

    id: str
    title: str | None = None
    url: str | None = None
    published: str | None = None
    sha256: str | None = None


class AboutInfo(BaseModel):
    """Answer of ``GET /about``."""

    version: str
    taxonomy_version: str
    catalog_codes: int
    catalog_fingerprint: str
    sources: list[AboutSource]
    # Disclaimer in English (the interface shows its own translation) and licence of the code.
    legal_notice: str | None = DISCLAIMER["en"]
    licence: str | None = LICENCE


@lru_cache
def reference_sources() -> tuple[AboutSource, ...]:
    """Legal texts, then the EBA files the reference data is built from, without duplicates."""
    sources = [AboutSource(id=key, url=url) for key, url in LEGAL_TEXTS]
    seen: set[str] = set()
    for name in PROVENANCE_FILES:
        provenance = json.loads((REFERENCE_DIR / name).read_text(encoding="utf-8"))
        for entry in provenance.get("inputs", []):
            digest = entry.get("sha256")
            if not entry.get("url") or digest in seen:
                continue  # a cross-reference to another provenance file
            seen.add(digest)
            sources.append(
                AboutSource(
                    id=f"eba_{entry['role']}",
                    title=entry.get("title"),
                    url=entry["url"],
                    published=entry.get("published") or entry.get("list_date"),
                    sha256=digest,
                )
            )
    return tuple(sources)


def about(version: str) -> AboutInfo:
    return AboutInfo(
        version=version,
        taxonomy_version=DEFAULT_VERSION,
        catalog_codes=len(load_catalog()),
        catalog_fingerprint=catalog_fingerprint(),
        sources=list(reference_sources()),
    )
