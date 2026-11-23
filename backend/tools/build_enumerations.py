# SPDX-License-Identifier: EUPL-1.2
"""Provenance and concordance of the closed lists (RT-12, #133, #153).

The codes of ``reference/dora/enumerations-4.0.json`` come from the EBA XBRL taxonomy 4.0
(``tools/build_reference.py``, AllowedValue of each table). The EBA workbook "List of possible
values for all data fields with drop downs" gives their labels. Both inputs are described in
``reference/dora/enumerations-4.0.provenance.json``.

This script checks, without any download and with the standard library only:
- that the workbook kept in ``reference/dora/sources/`` has the recorded SHA-256;
- that every list of the workbook equals a list of the JSON file, apart from the gaps the
  provenance file documents (decisions of the PO);
- that the labels of the JSON file are those of the workbook.

Usage::

    python -I tools/build_enumerations.py            # check, exit code 1 on a gap
    python -I tools/build_enumerations.py --labels   # also rewrite the labels from the workbook
"""

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

REFERENCE = Path(__file__).resolve().parent.parent / "reference" / "dora"
ENUMERATIONS = REFERENCE / "enumerations-4.0.json"
PROVENANCE = REFERENCE / "enumerations-4.0.provenance.json"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CODE = re.compile(r"^eba_[A-Za-z]+:\w+$")


# ------------------------------------------------------------------ workbook (stdlib reader)
def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def read_workbook(path: Path) -> dict[str, list[list[str]]]:
    """Sheet name -> rows of text cells (empty string for an empty cell)."""
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root]
        book = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        sheets: dict[str, list[list[str]]] = {}
        for sheet in book.find("m:sheets", NS):
            target = targets[sheet.get(f"{{{NS_REL}}}id")].lstrip("/")
            name = target if target.startswith("xl/") else f"xl/{target}"
            data = ElementTree.fromstring(archive.read(name))
            rows: list[list[str]] = []
            for row in data.iter(f"{{{NS['m']}}}row"):
                cells: dict[int, str] = {}
                for cell in row.findall("m:c", NS):
                    value = cell.find("m:v", NS)
                    inline = cell.find("m:is", NS)
                    if cell.get("t") == "s" and value is not None:
                        text = shared[int(value.text)]
                    elif inline is not None:
                        text = "".join(t.text or "" for t in inline.iter(f"{{{NS['m']}}}t"))
                    else:
                        text = value.text if value is not None and value.text else ""
                    cells[_column_index(cell.get("r"))] = text.strip()
                width = max(cells, default=-1) + 1
                rows.append([cells.get(i, "") for i in range(width)])
            sheets[sheet.get("name")] = rows
    return sheets


def workbook_lists(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    """(sheet, LIST header) -> {code: label}, read from the header row downwards.

    The header row is the first one holding a LIST… cell (blank rows may be absent from the XML).
    """
    lists: dict[tuple[str, str], dict[str, str]] = {}
    for sheet, rows in read_workbook(path).items():
        start = next((i for i, r in enumerate(rows) if any(c.startswith("LIST") for c in r)), None)
        if start is None:
            continue
        for index, name in enumerate(rows[start]):
            if not name.startswith("LIST"):
                continue
            values: dict[str, str] = {}
            for row in rows[start + 1 :]:
                code = row[index] if index < len(row) else ""
                if CODE.match(code):
                    label = row[index + 1] if index + 1 < len(row) else ""
                    values[code] = label
            lists[(sheet, name)] = values
    return lists


# ------------------------------------------------------------------ provenance and concordance
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_provenance() -> dict:
    return json.loads(PROVENANCE.read_text(encoding="utf-8"))


def labels_source() -> dict:
    return next(i for i in load_provenance()["inputs"] if i["role"] == "labels")


def _applies(gap: dict, sheet: str, header: str) -> bool:
    return gap["header"] == header and gap.get("sheet") in (None, sheet)


def concordance(path: Path) -> list[str]:
    """Undocumented differences between the workbook and the JSON lists (empty when all agree)."""
    gaps = load_provenance()["documented_gaps"]
    lists = {
        lst["id"]: {v["code"]: v["label"] for v in lst["values"]}
        for lst in json.loads(ENUMERATIONS.read_text(encoding="utf-8"))["lists"]
    }
    problems: list[str] = []
    matched: set[str] = set()
    for (sheet, header), values in sorted(workbook_lists(path).items()):
        codes = set(values)
        for gap in gaps:
            if _applies(gap, sheet, header):
                codes = (codes - set(gap.get("only_in_workbook", []))) | set(
                    gap.get("only_in_taxonomy", [])
                )
        same = [list_id for list_id, members in lists.items() if set(members) == codes]
        if not same:
            problems.append(f"{sheet}/{header}: {len(codes)} codes, no identical list")
            continue
        matched.update(same)
        for code, label in values.items():
            if code in lists[same[0]] and lists[same[0]][code] != label:
                problems.append(f"{sheet}/{header}: label of {code} differs")
    problems += [f"{list_id}: absent from the workbook" for list_id in sorted(set(lists) - matched)]
    return problems


def rewrite_labels(path: Path) -> None:
    labels: dict[str, str] = {}
    for values in workbook_lists(path).values():
        for code, label in values.items():
            labels.setdefault(code, label)
    data = json.loads(ENUMERATIONS.read_text(encoding="utf-8"))
    for lst in data["lists"]:
        for value in lst["values"]:
            value["label"] = labels.get(value["code"], value["label"])
    ENUMERATIONS.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", "utf-8")


def main(arguments: list[str]) -> int:
    source = labels_source()
    path = REFERENCE / source["local_copy"]
    found = sha256(path)
    if found != source["sha256"]:
        print(f"SHA-256 differs: {found} != {source['sha256']} ({path.name})")
        return 1
    if "--labels" in arguments:
        rewrite_labels(path)
    problems = concordance(path)
    for problem in problems:
        print(problem)
    print(f"{path.name}: SHA-256 ok, {len(problems)} undocumented difference(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
