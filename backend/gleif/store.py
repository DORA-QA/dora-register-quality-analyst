# SPDX-License-Identifier: EUPL-1.2
"""Reads the installed GLEIF copy (Parquet). Follows ``contracts.gleif.IGleifLookup``.

A register holds a few hundred LEI: each lookup reads only the row groups that may hold them
(Polars filters on the Parquet statistics; the files are sorted by LEI). Measured on the copy of
08/11/2026 (3.5 million LEI): 0.02 s for a few LEI, 0.15 s for 5 000, about 70 MB of memory.
"""

from pathlib import Path

import polars as pl

from contracts.gleif import GleifRecord, GleifSnapshot
from gleif.layout import current_dir, installed_manifest, root_dir

RECORD_COLUMNS = (
    "lei",
    "legal_name",
    "legal_country",
    "hq_country",
    "entity_status",
    "registration_status",
    "next_renewal",
    "successor_lei",
)


class ParquetGleifStore:
    """The copy installed under ``root`` (default: ``ROI_GLEIF_DIR``, else /data/gleif)."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or root_dir()

    @property
    def root(self) -> Path:
        return self._root

    @property
    def snapshot(self) -> GleifSnapshot | None:
        manifest = installed_manifest(self._root)
        if manifest is None:
            return None
        files = manifest.get("files", {})
        lei_file = files.get("lei.parquet", {}) if isinstance(files, dict) else {}
        return GleifSnapshot(
            content_date=str(manifest.get("content_date", "")),
            release=str(manifest.get("release", "")),
            lei_count=int(lei_file.get("rows", 0)) if isinstance(lei_file, dict) else 0,
        )

    def records(self, leis: set[str]) -> dict[str, GleifRecord]:
        if not leis:
            return {}
        frame = (
            pl.scan_parquet(current_dir(self._root) / "lei.parquet")
            .select(RECORD_COLUMNS)
            .filter(pl.col("lei").is_in(sorted(leis)))
            .collect()
        )
        return {row["lei"]: GleifRecord(**row) for row in frame.iter_rows(named=True)}

    def parents(self, leis: set[str], relationship: str) -> dict[str, str]:
        if not leis:
            return {}
        frame = (
            pl.scan_parquet(current_dir(self._root) / "rr.parquet")
            .filter(
                pl.col("child_lei").is_in(sorted(leis))
                & (pl.col("rel_type") == relationship)
                & (pl.col("rel_status") == "ACTIVE")
            )
            .select("child_lei", "parent_lei")
            .collect()
        )
        return {row["child_lei"]: row["parent_lei"] for row in frame.iter_rows(named=True)}
