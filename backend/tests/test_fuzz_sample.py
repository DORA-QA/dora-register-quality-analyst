# SPDX-License-Identifier: EUPL-1.2
"""Sampled fuzzing of the engine in the CI (red team RT-14, PO decision of 31/10/2026).

200 variants of the golden, drawn with a fixed seed: a column removed, or every value of a column
replaced by a trap value. No variant may stop a rule (ENG-001) or the API (HTTP 500).
"""

import csv
import io
import random

from fastapi.testclient import TestClient

from api.main import app
from tests.cases.golden import load_golden
from tests.factories import CLIENT_HEADERS

SEED = 20261031
VARIANTS = 200
TRAPS = (
    "",
    " ",
    "x" * 300,
    "-1",
    "2026-02-30",
    "NaN",
    "1e309",
    "#empty",
    '"',
    "‮",
    "eba_GA:ZZ",
    "0",
    "9999-12-31",
)


def _tables(package) -> list[tuple[str, list[str]]]:
    found = []
    for name, content in sorted(package.files.items()):
        if name.startswith("reports/b_") and name.endswith(".csv"):
            header = next(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
            found.append((name, [c for c in header if c.startswith("c")]))
    return found


def _variant(package, path: str, column: str, trap: str | None) -> None:
    reader = csv.reader(io.StringIO(package.files[path].decode("utf-8-sig")))
    header, *rows = list(reader)
    index = header.index(column)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    if trap is None:  # column removed
        writer.writerow(header[:index] + header[index + 1 :])
        writer.writerows(r[:index] + r[index + 1 :] for r in rows)
    else:
        writer.writerow(header)
        writer.writerows([*r[:index], trap, *r[index + 1 :]] for r in rows)
    package.files[path] = out.getvalue().encode("utf-8")


def _cases() -> list[tuple[str, str, str | None]]:
    rng = random.Random(SEED)
    tables = _tables(load_golden())
    cases = []
    for _ in range(VARIANTS):
        path, columns = rng.choice(tables)
        trap = None if rng.random() < 0.25 else rng.choice(TRAPS)
        cases.append((path, rng.choice(columns), trap))
    return cases


def test_no_variant_stops_a_rule_or_the_api():
    failures = []
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        for path, column, trap in _cases():
            package = load_golden()
            _variant(package, path, column, trap)
            response = client.post("/api/import", files={"file": (package.name, package.to_zip())})
            if response.status_code != 200:
                failures.append((path, column, trap, response.status_code))
                continue
            codes = {m["code"] for m in response.json()["messages"]}
            if "ENG-001" in codes:
                failures.append((path, column, trap, "ENG-001"))
    assert not failures, failures


def test_the_sample_mixes_removed_columns_and_trap_values():
    traps = [case[2] for case in _cases()]
    assert None in traps and len(set(traps) - {None}) >= 8
