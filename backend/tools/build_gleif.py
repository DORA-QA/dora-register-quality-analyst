# SPDX-License-Identifier: EUPL-1.2
"""Builds the GLEIF copy read by the backend (branch feature/gleif-local).

Reads the GLEIF files (LEI-CDF and RR-CDF, XML, Golden Copy or Concatenated Files, plain or
zipped) in one streaming pass, and writes into ``<out>``:

    lei.parquet     one row per LEI (duplicates of the Concatenated Files removed: ISSUED first,
                    then the latest update), sorted by LEI
    rr.parquet      relationships (child, parent, type, status), sorted by child
    manifest.json   date of the GLEIF publication, SHA-256, size and rows of each file

Measured on the files of 08/11/2026 (8.6 GB + 1.1 GB of XML): lei.parquet about 90 MB, rr.parquet
about 8 MB; about 8 minutes on one core. The rows are gathered in memory before sorting (about
1 GB for 3.5 million LEI).

Usage::

    uv run python -m tools.build_gleif --lei <lei2.xml|.zip> --rr <rr.xml|.zip> --out <folder>
    uv run python -m tools.build_gleif --manifest-only --out <folder> --content-date <ISO date>

Then publish with ``tools/publish_gleif_release.sh <folder>``.
"""

import argparse
import hashlib
import json
import sys
import time
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import IO

import polars as pl
from lxml import etree

from gleif.layout import DATA_FILES, MANIFEST, MANIFEST_FORMAT

BATCH = 100_000
Row = dict[str, str | None]


def _text(element: etree._Element, path: str) -> str | None:
    found = element.find(path)
    return found.text.strip() if found is not None and found.text else None


def lei_row(record: etree._Element) -> Row:
    successors = [
        e.text for e in record.iterfind("{*}Entity/{*}SuccessorEntity/{*}SuccessorLEI") if e.text
    ]
    return {
        "lei": _text(record, "{*}LEI"),
        "legal_name": _text(record, "{*}Entity/{*}LegalName"),
        "legal_country": _text(record, "{*}Entity/{*}LegalAddress/{*}Country"),
        "hq_country": _text(record, "{*}Entity/{*}HeadquartersAddress/{*}Country"),
        "entity_status": _text(record, "{*}Entity/{*}EntityStatus"),
        "registration_status": _text(record, "{*}Registration/{*}RegistrationStatus"),
        "next_renewal": (_text(record, "{*}Registration/{*}NextRenewalDate") or "")[:10] or None,
        "last_update": (_text(record, "{*}Registration/{*}LastUpdateDate") or "")[:10] or None,
        "successor_lei": "|".join(successors) or None,
    }


def rr_row(record: etree._Element) -> Row:
    return {
        "child_lei": _text(record, "{*}Relationship/{*}StartNode/{*}NodeID"),
        "parent_lei": _text(record, "{*}Relationship/{*}EndNode/{*}NodeID"),
        "rel_type": _text(record, "{*}Relationship/{*}RelationshipType"),
        "rel_status": _text(record, "{*}Relationship/{*}RelationshipStatus"),
        "reg_status": _text(record, "{*}Registration/{*}RegistrationStatus"),
    }


def _open(path: Path) -> IO[bytes]:
    if path.suffix.lower() == ".zip":
        archive = zipfile.ZipFile(path)
        inner = next(n for n in archive.namelist() if n.lower().endswith(".xml"))
        return archive.open(inner)
    return path.open("rb")


def content_date(path: Path) -> str | None:
    """ContentDate of the header of a GLEIF file (date of the publication)."""
    with _open(path) as handle:
        for _, element in etree.iterparse(handle, events=("end",), tag="{*}ContentDate"):
            return element.text.strip() if element.text else None
    return None


def _records(path: Path, tag: str, extract: Callable[[etree._Element], Row]) -> Iterator[Row]:
    with _open(path) as handle:
        for _, element in etree.iterparse(handle, events=("end",), tag="{*}" + tag, huge_tree=True):
            yield extract(element)
            element.clear()
            parent = element.getparent()
            while parent is not None and element.getprevious() is not None:
                del parent[0]


def _collect(rows: Iterator[Row], columns: tuple[str, ...]) -> pl.DataFrame:
    """Rows gathered by batches of BATCH (all columns are text)."""
    schema = dict.fromkeys(columns, pl.Utf8)
    frames: list[pl.DataFrame] = []
    batch: list[Row] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH:
            frames.append(pl.DataFrame(batch, schema=schema))
            batch = []
            print(f"  {len(frames) * BATCH:,}", flush=True)
    frames.append(pl.DataFrame(batch, schema=schema))
    return pl.concat(frames)


LEI_COLUMNS = (
    "lei",
    "legal_name",
    "legal_country",
    "hq_country",
    "entity_status",
    "registration_status",
    "next_renewal",
    "last_update",
    "successor_lei",
)
RR_COLUMNS = ("child_lei", "parent_lei", "rel_type", "rel_status", "reg_status")


def finish_lei(frame: pl.DataFrame, path: Path) -> int:
    """Remove the duplicates (Concatenated Files) and sort by LEI for fast lookups."""
    priority = (
        pl.when(pl.col("registration_status") == "ISSUED")
        .then(0)
        .when(pl.col("registration_status").str.starts_with("PENDING"))
        .then(2)
        .otherwise(1)
    )
    frame = (
        frame.with_columns(priority.alias("_p"))
        .sort(["lei", "_p", "last_update"], descending=[False, False, True], nulls_last=True)
        .unique("lei", keep="first", maintain_order=True)
        .drop("_p")
    )
    frame.write_parquet(path, compression="zstd", statistics=True, row_group_size=100_000)
    return frame.height


def finish_rr(frame: pl.DataFrame, path: Path) -> int:
    frame = frame.sort("child_lei")
    frame.write_parquet(path, compression="zstd", statistics=True, row_group_size=100_000)
    return frame.height


def write_manifest(out: Path, published: str, source: str) -> dict[str, object]:
    files: dict[str, dict[str, object]] = {}
    for name in DATA_FILES:
        data = (out / name).read_bytes()
        files[name] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "rows": pl.scan_parquet(out / name).select(pl.len()).collect().item(),
        }
    manifest: dict[str, object] = {
        "format": MANIFEST_FORMAT,
        "content_date": published,
        "source": source,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "builder": "backend/tools/build_gleif.py",
        "files": files,
    }
    (out / MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--lei", type=Path, help="LEI-CDF file (XML or ZIP)")
    parser.add_argument("--rr", type=Path, help="RR-CDF file (XML or ZIP)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source", default="GLEIF Golden Copy (LEI-CDF, RR-CDF)")
    parser.add_argument("--manifest-only", action="store_true", help="Parquet files already built")
    parser.add_argument("--content-date", help="Date of the GLEIF publication (ISO 8601)")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    if not args.manifest_only:
        if not args.lei or not args.rr:
            parser.error("--lei and --rr are required")
        start = time.time()
        leis = _collect(_records(args.lei, "LEIRecord", lei_row), LEI_COLUMNS)
        print(f"LEI: {finish_lei(leis, args.out / 'lei.parquet'):,} ({time.time() - start:.0f} s)")
        del leis
        links = _collect(_records(args.rr, "RelationshipRecord", rr_row), RR_COLUMNS)
        print(f"Relationships: {finish_rr(links, args.out / 'rr.parquet'):,}")
    published = args.content_date or (content_date(args.lei) if args.lei else None)
    if not published:
        parser.error("--content-date is required when no LEI file is given")
    manifest = write_manifest(args.out, published, args.source)
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
