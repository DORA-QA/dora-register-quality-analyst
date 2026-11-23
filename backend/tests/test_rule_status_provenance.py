# SPDX-License-Identifier: EUPL-1.2
"""The reference of the EBA rules comes from the official list (#127, RT-11, 31/10/2026)."""

import json
import re

from tools import build_rule_status as tool

ROOT = tool.BACKEND.parent
SHA = re.compile(r"^[0-9a-f]{64}$")


def test_provenance_records_url_date_and_fingerprint_of_every_source():
    provenance = tool.load_provenance()
    assert provenance["rules"] == "rule-status-4.0.json"
    roles = {source["role"]: source for source in provenance["inputs"]}
    assert set(roles) == {"rules", "deactivations", "taxonomy"}
    for source in roles.values():
        assert SHA.match(source["sha256"]), source["role"]
        assert source["status"].startswith("verified"), source["role"]
    for role in ("rules", "deactivations"):
        assert roles[role]["url"].startswith("https://www.eba.europa.eu/sites/default/files/")


def test_the_kept_list_has_the_recorded_fingerprint():
    source = tool.rules_source()
    assert tool.sha256(tool.REFERENCE / source["local_copy"]) == source["sha256"]


def test_rule_status_is_rebuilt_identically_from_the_official_list():
    payload, problems = tool.build(tool.REFERENCE / tool.rules_source()["local_copy"])
    assert problems == []
    assert payload == json.loads(tool.OUTPUT.read_text(encoding="utf-8"))
    rules = payload["rules"]
    assert (len(rules), sum(rule["active"] for rule in rules)) == (71, 49)
    # The 10 rules added after the taxonomy of March 2025 (PO-6 analysis of 18/10).
    assert sorted(r["id"] for r in rules if not r["in_taxonomy"]) == [
        "v8823_m",
        "v8824_m",
        *(f"v{n}_m" for n in range(8890, 8898)),
    ]


def test_cells_are_the_columns_named_by_the_expression():
    assert tool.cells_of("with {tB_01.02, default:null}: not ( isnull ({c0020-0090}) )") == (
        "c0020-0090"
    )
    assert tool.cells_of("with {tB_01.03}: not ( isnull ({c*}) )") == "c*"
    assert tool.cells_of("with {tB_05.01}: if not isnull({C0020}) then {c0020} and {c0110}") == (
        "c0020; c0110"
    )


def test_the_tool_exits_cleanly(capsys):
    assert tool.main([]) == 0
    assert "rule-status-4.0.json up to date" in capsys.readouterr().out


def test_the_export_of_the_professional_tool_is_gone():
    assert not (ROOT / "docs" / "sources" / "CONF-ReglesEBA.xlsx").exists()
