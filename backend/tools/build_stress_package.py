# SPDX-License-Identifier: EUPL-1.2
"""Build a very large, consistent and fictitious package for load tests (30/10/2026).

Usage (from backend/)::

    uv run python -I tools/build_stress_package.py 500000 ../stress-500000.sample.zip

The golden of the PO is the base. To it are added as many complete arrangements as needed for
B_05.01 to reach the number of rows requested. Each arrangement has:
- one direct provider (B_05.01) with its own fictitious LEI;
- one row of service in B_02.02, for the non-critical function F4 of the entity that maintains
  the register;
- its signatory (B_03.01), provider (B_03.02), user (B_04.01) and rank 1 (B_05.02).

The register therefore stays consistent: it raises the findings admitted for the golden, and
nothing more.

The LEIs start with ``ZZZZ``, a prefix assigned to no issuer (LOU). They have valid check
digits (ISO 17442), so they cannot be the code of a real entity. Everything else is invented.
"""

import csv
import io
import sys
import zipfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from tests import factories  # noqa: E402
from tests.cases.golden import load_golden  # noqa: E402

ENTITY = "529900P784EKW7VFMQ21"  # entity that maintains the register of the golden
LEI_TYPE = "eba_qCO:qx2000"
SERVICE = "eba_TA:S15"
PREFIX = "ZZZZ00"  # 4 characters of an unassigned issuer + 2 reserved characters


def fictitious_lei(number: int) -> str:
    """A LEI with valid check digits: PREFIX + 12 base-36 characters + 2 digits."""
    body = PREFIX + _base36(number).rjust(12, "0")
    remainder = int("".join(str(int(char, 36)) for char in body + "00")) % 97
    return f"{body}{98 - remainder:02d}"


def _base36(number: int) -> str:
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    text = ""
    while True:
        number, rest = divmod(number, 36)
        text = digits[rest] + text
        if number == 0:
            return text


def _table(files: dict[str, bytes], table: str) -> tuple[str, list[str], str]:
    path = f"reports/{table}.csv"
    text = files[path].decode("utf-8-sig")
    header = next(csv.reader(io.StringIO(text)))
    return path, header, text if text.endswith("\n") else text + "\n"


def _line(header: list[str], cells: dict[str, str]) -> str:
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerow([cells.get(c, "") for c in header])
    return out.getvalue()


def build(provider_rows: int) -> tuple[str, bytes, dict[str, int]]:
    """The golden plus enough arrangements for B_05.01 to hold ``provider_rows`` rows."""
    package = load_golden()
    files = package.files
    _, provider_header, provider_text = _table(files, "b_05.01")
    existing = provider_text.count("\n") - 1
    added = max(0, provider_rows - existing)

    rows_of = {
        "b_02.01": lambda c, p, i: {
            "c0010": c,
            "c0020": "eba_CO:x1",
            "c0040": "eba_CU:EUR",
            "c0050": str(1000 + i % 90000),
        },
        "b_02.02": lambda c, p, i: {
            "c0010": c,
            "c0020": ENTITY,
            "c0030": p,
            "c0040": LEI_TYPE,
            "c0050": "F4",
            "c0060": SERVICE,
            "c0070": "2025-01-01",
            "c0080": "9999-12-31",
            "c0100": "45",
            "c0110": "45",
            "c0120": "eba_GA:FR",
            "c0130": "eba_GA:FR",
            "c0140": "eba_BT:x29",
            "c0150": "eba_GA:qx2007",
            "c0160": "eba_GA:qx2007",
        },
        "b_03.01": lambda c, p, i: {"c0010": c, "c0020": ENTITY, "c0030": "true"},
        "b_03.02": lambda c, p, i: {"c0010": c, "c0020": p, "c0030": LEI_TYPE},
        "b_04.01": lambda c, p, i: {
            "c0010": c,
            "c0020": ENTITY,
            "c0030": "eba_ZZ:x839",
            "c0040": "Not Applicable",
        },
        "b_05.01": lambda c, p, i: {
            "c0010": p,
            "c0020": LEI_TYPE,
            "c0050": f"PRESTATAIRE FICTIF {i:07d}",
            "c0060": f"PRESTATAIRE FICTIF {i:07d}",
            "c0070": "eba_CT:x212",
            "c0080": "eba_GA:FR",
            "c0090": "eba_CU:EUR",
            "c0100": str(1000 + i % 90000),
            "c0110": p,
            "c0120": LEI_TYPE,
        },
        "b_05.02": lambda c, p, i: {
            "c0010": c,
            "c0020": SERVICE,
            "c0030": p,
            "c0040": LEI_TYPE,
            "c0050": "1",
            "c0060": p,
            "c0070": LEI_TYPE,
        },
    }
    for table, make in rows_of.items():
        path, header, text = _table(files, table)
        lines = [text]
        for i in range(added):
            lines.append(_line(header, make(f"CONTRAT FICTIF {i:07d}", fictitious_lei(i), i)))
        files[path] = "".join(lines).encode("utf-8")

    content = factories.build_zip(files=files, root=package.root, extra=package.extra)
    counts = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for info in archive.infolist():
            if "/reports/b_" in info.filename:
                name = info.filename.rsplit("/", 1)[-1][:-4].upper().replace("B_", "B_")
                counts[name] = archive.read(info).count(b"\n") - 1
        counts["uncompressed_mb"] = sum(i.file_size for i in archive.infolist()) // (1024 * 1024)
    return package.name, content, counts


def main(argv: list[str]) -> None:
    rows = int(argv[0]) if argv else 500_000
    target = Path(argv[1]) if len(argv) > 1 else Path(f"stress-{rows}.sample.zip")
    name, content, counts = build(rows)
    target.write_bytes(content)
    print(f"{target} ({len(content) // (1024 * 1024)} Mo, racine {name[:-4]})")
    for table, count in sorted(counts.items()):
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main(sys.argv[1:])
