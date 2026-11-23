# SPDX-License-Identifier: EUPL-1.2
"""Rebuild backend/reference/dora/*-4.0.json from the official EBA files.

Usage (needs openpyxl, which is NOT a runtime dependency of the product)::

    python -I tools/build_reference.py FRAMEWORKS_DIR SEVERITY_DIR VALUES_XLSX OUT_DIR

Inputs: the unzipped "EBA XBRL 4.0 Reporting Frameworks" and "Severity" packages and the
EBA workbook "List of possible values ... drop downs". Nothing is downloaded.
"""

import json
import re
import sys
from pathlib import Path

from lxml import etree

TABLE_RE = re.compile(r"^B_(\d{2})-(\d{2})$")
NOT_EMPTY = re.compile(r"^not\(empty\(\{(B_\d{2}\.\d{2}),,(\d{4}),\}\)\)$")
RULE_MSG = re.compile(r"^([a-z]\d+_[a-z]+_\d+):\s*(.*?)\s+Fails because", re.S)
NS_LABEL = "http://xbrl.org/2008/label"
NS_MSG = "http://xbrl.org/2010/message"
NS_LINK = "http://www.xbrl.org/2003/linkbase"
XLINK = "http://www.w3.org/1999/xlink"


def find(root: Path, *parts: str) -> Path:
    matches = list(root.rglob("/".join(parts)))
    if not matches:
        raise SystemExit(f"not found: {'/'.join(parts)}")
    return matches[0]


def concept_labels(table_dir: Path, code: str) -> dict[str, str]:
    """concept qname -> English label, through the rendering and label linkbases."""
    rend = etree.parse(str(table_dir / f"{code}-rend.xml"))
    node_concept: dict[str, str] = {}
    for node in rend.iter("{*}ruleNode"):
        qname = node.find(".//{*}qname")
        if qname is not None and qname.text:
            node_concept[node.get("id")] = qname.text.strip()
    labels = etree.parse(str(table_dir / f"{code}-lab-en.xml"))
    loc_to_node = {
        loc.get(f"{{{XLINK}}}label"): loc.get(f"{{{XLINK}}}href").split("#")[1]
        for loc in labels.iter(f"{{{NS_LINK}}}loc")
    }
    label_text = {
        lab.get(f"{{{XLINK}}}label"): (lab.text or "").strip()
        for lab in labels.iter(f"{{{NS_LABEL}}}label")
    }
    result: dict[str, str] = {}
    for arc in labels.iter("{*}arc"):
        node = loc_to_node.get(arc.get(f"{{{XLINK}}}from"))
        text = label_text.get(arc.get(f"{{{XLINK}}}to"))
        if node in node_concept and text:
            result[node_concept[node]] = text
    return result


def code_labels(values_xlsx: Path) -> dict[str, str]:
    import openpyxl

    mapping: dict[str, str] = {}
    workbook = openpyxl.load_workbook(values_xlsx, read_only=True)
    for sheet in workbook:
        for row in sheet.iter_rows(min_row=5, values_only=True):
            for left, right in zip(row, row[1:], strict=False):
                if isinstance(left, str) and re.match(r"^eba_[A-Za-z]+:\w+$", left) and right:
                    mapping.setdefault(left, str(right).strip())
    return mapping


def main(frameworks: Path, severity: Path, values_xlsx: Path, out: Path) -> None:
    dora = find(frameworks, "fws", "dora", "4.0")
    labels_by_code = code_labels(values_xlsx)

    columns: list[dict] = []
    fields: list[dict] = []
    lists: dict[frozenset[str], dict] = {}
    for table_json in sorted((dora / "tab").glob("b_*/b_*.json")):
        template = json.loads(table_json.read_text(encoding="utf-8"))["tableTemplates"]
        ((key, spec),) = template.items()
        match = TABLE_RE.match(key)
        table = f"B_{match.group(1)}.{match.group(2)}"
        concept_label = concept_labels(table_json.parent, table_json.stem)
        primary = spec.get("tc:keys", {}).get("primary", {}).get("fields", [])
        references = spec.get("tc:keys", {}).get("reference", [])
        for column, column_spec in spec["columns"].items():
            doc = column_spec.get("eba:documentation", {})
            concept = (column_spec.get("dimensions") or {}).get("concept")
            allowed = sorted(doc.get("AllowedValue", {}))
            enumeration = None
            if allowed:
                lst = lists.setdefault(
                    frozenset(allowed),
                    {"id": f"L{len(lists) + 1:02d}", "codes": allowed, "used_by": []},
                )
                lst["used_by"].append(f"{table}.{column[1:]}")
                enumeration = lst["id"]
            refs = [
                {
                    "name": r["name"],
                    "target_table": r["keyRef"]["tableTemplate"].replace("-", ".")[0:],
                }
                for r in references
                if column in r["columns"]
            ]
            columns.append(
                {
                    "table": table,
                    "column": column,
                    "reference": f"{table}.{column[1:]}",
                    "status": "confirmed",
                    "note": (
                        "Check column set by the regulator (boolean), see sprint-1-hypotheses"
                        if (table, column)
                        in {("B_02.03", "c0030"), ("B_03.01", "c0030"), ("B_03.03", "c0031")}
                        else None
                    ),
                }
            )
            fields.append(
                {
                    "table": table,
                    "code": f"{table}.{column[1:]}",
                    "csv_column": column,
                    "name": concept_label.get(concept) if concept else None,
                    "type": doc.get("type"),
                    "enumeration": enumeration,
                    "primary_key": column in primary,
                    "mandatory": False,
                    "references": refs,
                }
            )

    # Rules: one file per assertion; message looks like "v8821_m_0: expression Fails because ...".
    rules: list[dict] = []
    mandatory: set[str] = set()
    for rule_file in sorted((dora / "val").glob("vr-*.xml")):
        tree = etree.parse(str(rule_file))
        for message in tree.iter(f"{{{NS_MSG}}}message"):
            text = " ".join("".join(message.itertext()).split())
            found = RULE_MSG.match(text)
            if not found:
                continue
            expression = found.group(2).replace("{{", "{").replace("}}", "}")
            rules.append({"id": found.group(1), "expression": expression, "severity": "warning"})
            single = NOT_EMPTY.match(expression.replace("{{", "{").replace("}}", "}"))
            if single:
                mandatory.add(f"{single.group(1)}.{single.group(2)}")
    unique = {r["id"]: r for r in rules}
    for field in fields:
        field["mandatory"] = field["code"] in mandatory

    sev_file = find(severity, "fws", "dora", "4.0", "set", "dora-val-severity.xml")
    severities = set(re.findall(r"severities\.xml#(\w+)", sev_file.read_text(encoding="utf-8")))

    enumerations = [
        {
            "id": lst["id"],
            "used_by": lst["used_by"],
            "values": [{"code": c, "label": labels_by_code.get(c)} for c in lst["codes"]],
        }
        for lst in lists.values()
    ]
    out.mkdir(parents=True, exist_ok=True)
    source = "EBA reporting framework 4.0, DORA module"
    dump = lambda name, payload: (out / name).write_text(  # noqa: E731
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    dump("columns-4.0.json", {"source": source, "columns": columns})
    dump(
        "fields-4.0.json",
        {"source": source, "reference_convention": "B_xx.xx.xxxx", "fields": fields},
    )
    dump("enumerations-4.0.json", {"source": source, "lists": enumerations})
    dump(
        "validation-rules-4.0.json",
        {
            "source": source,
            "severities_in_package": sorted(severities),
            "rules": list(unique.values()),
        },
    )
    print(
        f"{len(columns)} columns, {len(enumerations)} lists, "
        f"{sum(len(e['values']) for e in enumerations)} codes, {len(unique)} rules, "
        f"{len(mandatory)} mandatory, severities={sorted(severities)}"
    )


if __name__ == "__main__":
    main(*(Path(arg) for arg in sys.argv[1:5]))
