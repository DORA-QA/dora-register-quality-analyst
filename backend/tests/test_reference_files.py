# SPDX-License-Identifier: EUPL-1.2
"""Consistency of the reference files generated from the EBA taxonomy."""

import json
import re
from pathlib import Path

from contracts import data_model

REFERENCE = Path(__file__).resolve().parent.parent / "reference" / "dora"


def _load(name: str) -> dict:
    return json.loads((REFERENCE / name).read_text(encoding="utf-8"))


def test_every_template_of_the_version_has_columns() -> None:
    versions = _load("versions.json")["versions"]["4.0"]["templates"]
    columns = _load("columns-4.0.json")["columns"]
    assert len(columns) == 120
    assert {c["table"] for c in columns} == set(versions)


def test_references_use_the_eba_style() -> None:
    for column in _load("columns-4.0.json")["columns"]:
        assert re.fullmatch(r"B_\d{2}\.\d{2}\.\d{4}", column["reference"])
    for field in _load("fields-4.0.json")["fields"]:
        assert re.fullmatch(r"B_\d{2}\.\d{2}\.\d{4}", field["code"])


def test_check_columns_are_noted() -> None:
    noted = {c["reference"] for c in _load("columns-4.0.json")["columns"] if c["note"]}
    assert noted == {"B_02.03.0030", "B_03.01.0030", "B_03.03.0031"}


def test_enumerations_are_labelled_and_referenced() -> None:
    lists = _load("enumerations-4.0.json")["lists"]
    ids = {lst["id"] for lst in lists}
    assert all(value["label"] for lst in lists for value in lst["values"])
    used = {f["enumeration"] for f in _load("fields-4.0.json")["fields"] if f["enumeration"]}
    assert used == ids


def test_validation_rules_and_mandatory_fields() -> None:
    rules = _load("validation-rules-4.0.json")["rules"]
    assert len(rules) == 93
    assert len({r["id"] for r in rules}) == 93
    mandatory = [f for f in _load("fields-4.0.json")["fields"] if f["mandatory"]]
    assert len(mandatory) == 41


def test_rule_status_matches_the_eba_list() -> None:
    rules = data_model.rule_status()
    assert len(rules) == 71
    assert len(data_model.active_rules()) == 49
    assert sum(not rule.active for rule in rules.values()) == 22
    # Official EBA list VR_4.4.phase1 (October 2026), same DORA content as the list of 14/09/2026.
    assert _load("rule-status-4.0.json")["list"] == "VR_4.4.phase1"


def test_every_taxonomy_rule_is_in_the_status_list() -> None:
    taxonomy = {re.sub(r"_\d+$", "", r["id"]) for r in _load("validation-rules-4.0.json")["rules"]}
    rules = data_model.rule_status()
    assert taxonomy <= set(rules)
    missing = {rule.id for rule in rules.values() if not rule.in_taxonomy}
    assert missing == {"v8823_m", "v8824_m", *(f"v{n}_m" for n in range(8890, 8898))}


def test_existence_rules_are_all_inactive() -> None:
    existence = [rule for rule in data_model.rule_status().values() if rule.kind == "existence"]
    assert len(existence) == 9
    assert not any(rule.active for rule in existence)
    assert [rule.id for rule in data_model.active_rules() if rule.id.startswith("v8826")] == [
        "v8826_m"
    ]
