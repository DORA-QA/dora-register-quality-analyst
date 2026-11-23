# SPDX-License-Identifier: EUPL-1.2
"""Measure the import + validation pipeline on a synthetic package (CL-11).

Usage (from backend/)::

    uv run python -I tools/measure_performance.py [ROWS ...]
    uv run python -I tools/measure_performance.py --joins [ROWS ...]
    uv run python -I tools/measure_performance.py --export [ROWS ...]

For each requested size (default: 1000 10000 50000) a fictitious package is built in memory with
that many rows in B_05.01, imported through the real ``ImportService`` and the API response is
built. With ``--joins`` (Sprint 3, brief §17.5), the golden register is copied arrangement by
arrangement (references suffixed ``#k``) until B_02.02 holds at least that many rows: every
cross-table rule then runs on a consistent register. Reported: duration, rows, findings,
response weight and memory. With ``--export`` (Sprint 4, brief §31.4, CL-40), the same
synthetic package is imported, then every occurrence of the largest finding is read page by page,
and the whole report is exported as CSV and JSON Lines (streamed into a counter, never to disk):
durations, sizes, memory kept by the analysis and memory peak of each export. Everything is
invented, no real register data is used and nothing leaves the machine.
"""

import csv
import io
import math
import resource
import sys
import tempfile
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from api.config import APP_VERSION, get_settings  # noqa: E402
from api.services.import_service import (  # noqa: E402
    ImportOutcome,
    ImportService,
    build_response,
    occurrences_page,
    ordered_messages,
)
from contracts.naming import file_name_from_table_code  # noqa: E402
from dataset.store import DatasetStore  # noqa: E402
from reports import export  # noqa: E402
from scoring import profile_of_code  # noqa: E402
from tests import factories  # noqa: E402
from tests.cases.golden import load_golden  # noqa: E402

DEFAULT_SIZES = (1_000, 10_000, 50_000)


@dataclass
class Measure:
    scenario: str
    rows_requested: int
    rows_loaded: int
    zip_kb: int
    seconds: float
    findings: int
    occurrences: int
    response_kb: int
    peak_python_mb: float
    peak_process_mb: float


def synthetic_files(rows: int, defect_every: int = 0) -> dict[str, bytes]:
    """The default package, with ``rows`` fictitious providers in B_05.01.

    With ``defect_every`` > 0, one row in that many gets an empty mandatory name and an unknown
    country, to produce findings with many occurrences.
    """
    files = factories.default_files()
    providers = [
        {
            "c0010": f"PROV{i:016d}",
            "c0020": "eba_qCO:qx2003",
            "c0050": f"Provider {i}",
            "c0060": f"Provider {i}",
            "c0070": "eba_CT:x212",
            "c0080": "eba_GA:FR",
            "c0110": "552032534",
            "c0120": "eba_qCO:qx2003",
        }
        for i in range(rows)
    ]
    if defect_every:
        for provider in providers[::defect_every]:
            provider.update({"c0050": "", "c0080": "eba_GA:ZZ"})
    files["reports/b_05.01.csv"] = factories.table_csv("B_05.01", *providers)
    return files


# Columns holding a reference number of arrangement (B_02.01.0010), from the key constraints.
ARRANGEMENT_COLUMNS = {
    "B_02.01": ("c0010", "c0030"),
    "B_02.02": ("c0010",),
    "B_02.03": ("c0010", "c0020"),
    "B_03.01": ("c0010",),
    "B_03.02": ("c0010",),
    "B_03.03": ("c0010",),
    "B_04.01": ("c0010",),
    "B_05.02": ("c0010",),
    "B_07.01": ("c0010",),
}


def relational_package(rows: int) -> tuple[str, bytes, int]:
    """The golden, copied arrangement by arrangement until B_02.02 has at least ``rows`` rows.

    Returns the file name, the ZIP and the number of rows of B_02.02.
    """
    package = load_golden()
    path = f"reports/{file_name_from_table_code('B_02.02')}"
    per_copy = len(list(csv.reader(io.StringIO(package.files[path].decode("utf-8-sig"))))) - 1
    copies = max(1, math.ceil(rows / per_copy))
    for table, columns in ARRANGEMENT_COLUMNS.items():
        name = f"reports/{file_name_from_table_code(table)}"
        if name not in package.files:
            continue
        reader = csv.reader(io.StringIO(package.files[name].decode("utf-8-sig")))
        header = next(reader)
        original = list(reader)
        indexes = [header.index(c) for c in columns if c in header]
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(header)
        for k in range(copies):
            for row in original:
                copy = list(row)
                for i in indexes:
                    if copy[i]:
                        copy[i] = f"{copy[i]} #{k}"
                writer.writerow(copy)
        package.files[name] = out.getvalue().encode()
    return package.name, package.to_zip(), copies * per_copy


def measure(rows: int, defect_every: int = 0, joins: bool = False) -> Measure:
    settings = get_settings()
    if joins:
        file_name, content, rows = relational_package(rows)
        scenario = "jointures (golden copié)"
    else:
        file_name = f"{factories.PACKAGE_NAME}.zip"
        content = factories.build_zip(files=synthetic_files(rows, defect_every))
        scenario = "10 % de lignes défectueuses" if defect_every else "conforme"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / file_name
        path.write_bytes(content)
        # Two runs: tracemalloc slows Python down about five times, so the duration is timed
        # without it, and the Python memory peak is read in a second, traced run (30/10).
        service = ImportService(settings, DatasetStore(ttl_seconds=60))
        started = time.perf_counter()
        outcome = service.run(path, path.name)
        response = build_response(outcome)
        seconds = time.perf_counter() - started
        service.forget()
        tracemalloc.start()
        traced = ImportService(settings, DatasetStore(ttl_seconds=60))
        build_response(traced.run(path, path.name))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        traced.forget()
    body = response.model_dump_json()
    occurrences = sum(m.occurrences_total for m in response.messages)
    return Measure(
        scenario=scenario,
        rows_requested=rows,
        rows_loaded=outcome.rows_loaded,
        zip_kb=len(content) // 1024,
        seconds=seconds,
        findings=len(response.messages),
        occurrences=occurrences,
        response_kb=len(body.encode()) // 1024,
        peak_python_mb=peak / 1024 / 1024,
        # ru_maxrss is in kilobytes on Linux (bytes on macOS).
        peak_process_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        / (1024 if sys.platform != "darwin" else 1024 * 1024),
    )


@dataclass
class ExportMeasure:
    rows: int
    import_seconds: float
    findings: int
    occurrences: int
    kept_mb: float
    pages_seconds: float
    pages_read: int
    csv_seconds: float
    csv_mb: float
    csv_peak_mb: float
    jsonl_seconds: float
    jsonl_mb: float
    jsonl_peak_mb: float


def _export_once(outcome: ImportOutcome, kind: str) -> tuple[float, int]:
    """Stream the whole report into a counter: (seconds, bytes). Nothing is written."""
    lines = export.rows(
        ordered_messages(outcome),
        import_id=outcome.import_id,
        engine_version=APP_VERSION,
        language="fr",
        profile_of=profile_of_code,
    )
    stream = export.csv_stream(lines) if kind == "csv" else export.jsonl_stream(lines)
    started = time.perf_counter()
    size = sum(len(chunk.encode("utf-8")) for chunk in stream)
    return time.perf_counter() - started, size


def measure_export(rows: int) -> ExportMeasure:
    settings = get_settings()
    content = factories.build_zip(files=synthetic_files(rows, defect_every=10))
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"{factories.PACKAGE_NAME}.zip"
        path.write_bytes(content)
        # Memory kept by one analysis: traced run, register released, findings kept (RT-13).
        traced = ImportService(settings, DatasetStore(ttl_seconds=60))
        tracemalloc.start()
        kept = traced.run(path, path.name)
        traced.forget()
        kept_mb = tracemalloc.get_traced_memory()[0] / 1024 / 1024
        tracemalloc.stop()
        del kept
        # Duration: untraced run (tracemalloc slows Python down about five times, 30/10).
        service = ImportService(settings, DatasetStore(ttl_seconds=60))
        started = time.perf_counter()
        outcome = service.run(path, path.name)
        response = build_response(outcome)
        import_seconds = time.perf_counter() - started

        biggest = max(response.messages, key=lambda m: m.occurrences_available)
        started = time.perf_counter()
        offset, read = 0, 0
        while True:
            page = occurrences_page(outcome, biggest.index or 0, offset, 1000)
            if page is None or not page.occurrences:
                break
            read += len(page.occurrences)
            offset += 1000
        pages_seconds = time.perf_counter() - started

        results = {}
        for kind in ("csv", "jsonl"):
            seconds, size = _export_once(outcome, kind)
            tracemalloc.start()
            _export_once(outcome, kind)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            results[kind] = (seconds, size / 1024 / 1024, peak / 1024 / 1024)
        service.forget()
    return ExportMeasure(
        rows=rows,
        import_seconds=import_seconds,
        findings=len(response.messages),
        occurrences=sum(len(m.occurrences) for m in outcome.messages),
        kept_mb=kept_mb,
        pages_seconds=pages_seconds,
        pages_read=read,
        csv_seconds=results["csv"][0],
        csv_mb=results["csv"][1],
        csv_peak_mb=results["csv"][2],
        jsonl_seconds=results["jsonl"][0],
        jsonl_mb=results["jsonl"][1],
        jsonl_peak_mb=results["jsonl"][2],
    )


def render_export(measures: list[ExportMeasure]) -> str:
    lines = [
        "| Lignes B_05.01 | Import (s) | Constats | Occurrences gardées | Mémoire gardée (Mo) "
        "| Lecture par pages (s) | Export CSV (s) | CSV (Mo) | Pic CSV (Mo) "
        "| Export JSON Lines (s) | JSON Lines (Mo) | Pic JSON Lines (Mo) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {m.rows} | {m.import_seconds:.2f} | {m.findings} | {m.occurrences} | {m.kept_mb:.0f} "
        f"| {m.pages_seconds:.2f} ({m.pages_read}) | {m.csv_seconds:.2f} | {m.csv_mb:.1f} "
        f"| {m.csv_peak_mb:.1f} | {m.jsonl_seconds:.2f} | {m.jsonl_mb:.1f} "
        f"| {m.jsonl_peak_mb:.1f} |"
        for m in measures
    ]
    return "\n".join(lines)


def render(measures: list[Measure]) -> str:
    lines = [
        "| Scénario | Lignes (B_05.01 ou B_02.02) | Lignes chargées | ZIP (Ko) | Durée (s) "
        "| Constats | Occurrences | Réponse API (Ko) | Pic Python (Mo) | Pic processus (Mo) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {m.scenario} | {m.rows_requested} | {m.rows_loaded} | {m.zip_kb} | {m.seconds:.2f} "
        f"| {m.findings} | {m.occurrences} | {m.response_kb} | {m.peak_python_mb:.0f} "
        f"| {m.peak_process_mb:.0f} |"
        for m in measures
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    joins = "--joins" in argv
    sizes = tuple(int(a) for a in argv if not a.startswith("--")) or DEFAULT_SIZES
    if "--export" in argv:
        print(render_export([measure_export(size) for size in sizes]))
        return
    if joins:
        runs = [measure(size, joins=True) for size in sizes]
    else:
        runs = [measure(size, defect_every) for size in sizes for defect_every in (0, 10)]
    print(render(runs))


if __name__ == "__main__":
    main(sys.argv[1:])
