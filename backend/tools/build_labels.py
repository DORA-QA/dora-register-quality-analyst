# SPDX-License-Identifier: EUPL-1.2
"""Build backend/reference/dora/labels-4.0.json from the official texts of the ITS 2024/2956 (#179).

The PO decided on 04/11/2026 that the findings show the official labels of the columns and of
the closed-list values, in French and in English, taken from the Commission Implementing
Regulation (EU) 2024/2956 (OJ L, 2.12.2024). Both language versions are kept in
``reference/dora/sources/`` (``its-2024-2956-en.pdf``, ``its-2024-2956-fr.pdf``).

- Column names: read from Annex I, row by row (column code, column name).
- Corrigendum of 19/09/2025 (OJ L, 2025/90725, kept in both languages in ``sources/``): the
  renumbering of B_06.01 (ITS 0060 → 0050 … 0110 → 0100, as in the EBA taxonomy 4.0) is read
  from it, and the corrected column names (B_05.01.0090) replace those of 2024.
- Template titles: the heading "Instructions to complete template B_xx.xx — <title>" of Annex I,
  copied in ``labels-members-4.0.json`` and checked against the PDF.
- List values: ``reference/dora/labels-members-4.0.json`` maps each EBA code to its ITS option,
  with the text copied from the ITS. This script checks that each text is in the PDF, except the
  few cells marked ``checked_by_hand`` (cells of tables wrapped over several columns).

Usage (from backend/)::

    uv run --group dev python -I tools/build_labels.py           # check, exit 1 on a gap
    uv run --group dev python -I tools/build_labels.py --write   # rewrite labels-4.0.json
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import pdfplumber

REFERENCE = Path(__file__).resolve().parent.parent / "reference" / "dora"
SOURCES = REFERENCE / "sources"
OUTPUT = REFERENCE / "labels-4.0.json"
MEMBERS = REFERENCE / "labels-members-4.0.json"
FIELDS = REFERENCE / "fields-4.0.json"
PDF = {
    "en": (
        "its-2024-2956-en.pdf",
        "4ffa3dd7c22ac10e1e4bdaf45cf067bcd7fd12dc1603cc0bd7fd63499b037050",
    ),
    "fr": (
        "its-2024-2956-fr.pdf",
        "61826edc81630903b5315eb708a25e605b7d1aa207221e6b9f8bb946eb24f156",
    ),
}
CORRIGENDUM = {
    "en": (
        "its-2024-2956-corrigendum-2025-09-19-en.pdf",
        "fc48183e6de026f12ade7ffb76c0e79f9ca1a022a19bd408c9611bdcbe5666d2",
    ),
    "fr": (
        "its-2024-2956-corrigendum-2025-09-19-fr.pdf",
        "8ff2e5f72a8634063322e5fc07a0c399df6143401167ef4e1154aca44034b3c0",
    ),
}
# Column names replaced by the corrigendum: code → language → (text of 2024, corrected text).
CORRECTED_NAMES = {
    "B_05.01.0090": {
        "en": (
            "Currency of the amount reported in B_05.01.0070",
            "Currency of the amount reported in B_05.01.0100",
        ),
        "fr": (
            "Monnaie du montant déclaré dans la colonne B_05.01.0070",
            "Monnaie du montant déclaré dans la colonne B_05.01.0100",
        ),
    },
}
RENUMBERED = re.compile(r"for: '(B_\d{2}\.\d{2}\.\d{4})' read: '(B_\d{2}\.\d{2}\.\d{4})'")
CODE = re.compile(r"B_\d{2}\.\d{2}\.\d{4}")


def _clean(text: str) -> str:
    text = re.sub(r"(\w)- (\w)", r"\1-\2", text)  # "third- party" cut at the end of a line
    return re.sub(r"\s+", " ", text).strip()


def _lines(words: list[dict], x0: float, x1: float, top: float, bottom: float) -> str:
    found = [w for w in words if x0 <= w["x0"] < x1 and top - 1 <= w["top"] < bottom - 1]
    found.sort(key=lambda w: (round(w["top"] / 2), w["x0"]))
    return _clean(" ".join(w["text"] for w in found))


def column_names(pdf_path: Path) -> dict[str, str]:
    """Column code → column name, as numbered in the ITS."""
    names: dict[str, str] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            for table in page.find_tables():
                for row in table.rows:
                    cells = [c for c in row.cells if c]
                    if len(cells) < 3:
                        continue
                    top, bottom = row.bbox[1], row.bbox[3]
                    code = CODE.search(_lines(words, 0, cells[0][0] - 1, top, bottom))
                    if code and code.group(0) not in names:
                        names[code.group(0)] = _lines(words, cells[0][0], cells[0][2], top, bottom)
    return names


def _read(file_name: str, sha: str) -> str:
    path = SOURCES / file_name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != sha:
        raise SystemExit(f"{file_name}: SHA-256 {digest} differs from the recorded one")
    with pdfplumber.open(path) as pdf:
        return " ".join(p.extract_text() or "" for p in pdf.pages)


def corrigendum() -> tuple[dict[str, str], dict[str, str]]:
    """Renumbered column codes (2024 → corrected) and the normalised text of each language."""
    texts = {language: _read(*source) for language, source in CORRIGENDUM.items()}
    plain = _clean(texts["en"].replace("\n", " ").replace("‘", "'").replace("’", "'"))
    renumbered = dict(RENUMBERED.findall(plain))
    if not renumbered:
        raise SystemExit("No renumbered column found in the corrigendum")
    return renumbered, {language: _normalised(text) for language, text in texts.items()}


def _normalised(text: str) -> str:
    text = _clean(text.replace("\n", " ")).replace("’", "'").lower()
    return re.sub(r"[«»]", "", text)


def build() -> dict:
    texts: dict[str, str] = {}
    names: dict[str, dict[str, str]] = {}
    known = {f["code"] for f in json.loads(FIELDS.read_text("utf-8"))["fields"]}
    renumbered, corrected = corrigendum()
    for language, (file_name, sha) in PDF.items():
        texts[language] = _normalised(_read(file_name, sha))
        for code, name in column_names(SOURCES / file_name).items():
            target = renumbered.get(code, code)
            if target in known:
                names.setdefault(target, {})[language] = name
    for code, by_language in CORRECTED_NAMES.items():
        for language, (old, new) in by_language.items():
            if names[code][language] != old or _normalised(new) not in corrected[language]:
                raise SystemExit(f"{code} ({language}): correction no longer matches the texts")
            names[code][language] = new

    curated = json.loads(MEMBERS.read_text("utf-8"))
    members: dict[str, dict[str, str]] = {}
    gaps = []
    for item in curated["members"]:
        for language in ("en", "fr"):
            if (
                not item.get("checked_by_hand")
                and _normalised(item[language]) not in texts[language]
            ):
                gaps.append(f"{item['code']} ({language}): « {item[language]} » not in the ITS")
        members[item["code"]] = {"en": item["en"], "fr": item["fr"]}
    tables: dict[str, dict[str, str]] = {}
    for item in curated["tables"]:
        for language in ("en", "fr"):
            if _normalised(f"{item['code']} — {item[language]}") not in texts[language].replace(
                "—", " — "
            ).replace("  ", " "):
                gaps.append(f"{item['code']} ({language}): title not in the ITS")
        tables[item["code"]] = {"en": item["en"], "fr": item["fr"]}
    if gaps:
        raise SystemExit("\n".join(gaps))
    return {
        "source": {
            "en": (
                "Commission Implementing Regulation (EU) 2024/2956, OJ L, 2.12.2024 "
                "(Annexes I and III)"
            ),
            "fr": "Règlement d'exécution (UE) 2024/2956, JO L du 2.12.2024 (annexes I et III)",
            "corrigendum": "OJ L, 2025/90725, 19.9.2025",
            "built_by": "tools/build_labels.py",
            "decided": curated["decided"],
        },
        "status": "OFFICIAL",
        "fields": dict(sorted(names.items())),
        "members": dict(sorted(members.items())),
        "tables": dict(sorted(tables.items())),
    }


def main() -> int:
    built = json.dumps(build(), ensure_ascii=False, indent=1) + "\n"
    if "--write" in sys.argv:
        OUTPUT.write_text(built, encoding="utf-8")
        print(f"{OUTPUT.name} written")
        return 0
    if OUTPUT.read_text(encoding="utf-8") != built:
        print(f"{OUTPUT.name} differs from the ITS: run with --write")
        return 1
    print(f"{OUTPUT.name} matches the ITS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
