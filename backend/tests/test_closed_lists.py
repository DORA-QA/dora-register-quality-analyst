# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 6: closed lists (DAT-033) and provenance of the lists (RT-12, #133, #153).

For the check (brief §17.1): compliant case, non-compliant case, limit case, absent table,
empty value, documented exception, location of the occurrences, origin and status.
"""

import json
import re

import pytest

from contracts import data_model
from contracts.check_report import load_registry
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import load_catalog
from rules.engine import RulesEngine
from rules.technical.enumerations import ClosedListRule
from tests.test_technical_rules import frame
from tools import build_enumerations as tool


def run(**tables):
    found = {table: frame(table, *rows) for table, rows in tables.items()}
    return RulesEngine([ClosedListRule()]).run(RoIDataset("ZIP", PackageMetadata(), found)).messages


def function(impact="eba_ZZ:x793", critical="eba_BT:x28", kind="eba_TA:x182"):
    return {"c0010": "F1", "c0020": kind, "c0050": critical, "c0100": impact}


# ------------------------------------------------------------------ the 41 fields
def test_the_taxonomy_has_41_fields_with_a_closed_list():
    lists = data_model.closed_lists()
    assert len(lists) == 41
    assert len({c.id for c in lists.values()}) == 21
    assert lists[("B_05.01", "c0040")].id == "L07"


# ------------------------------------------------------------------ compliant, absent, empty
def test_codes_of_the_lists_raise_nothing():
    assert run(**{"B_06.01": [function()]}) == []


def test_absent_table_and_empty_values_raise_nothing():
    assert run() == []
    assert run(**{"B_06.01": [function(impact="", critical="  ")]}) == []


# ------------------------------------------------------------------ non-compliant
def test_dat_033_one_finding_per_column_with_its_list_and_occurrences():
    messages = run(**{"B_06.01": [function(impact="High"), function(impact="x793", kind="ABC")]})
    by_column = {m.params["column"].code: m for m in messages}
    assert set(by_column) == {"B_06.01.0020", "B_06.01.0100"}
    impact = by_column["B_06.01.0100"]
    assert impact.code == "DAT-033" and impact.params["list"] == "L18"
    assert [(o.row, o.column, o.value) for o in impact.occurrences] == [
        (1, "c0100", "High"),
        (2, "c0100", "x793"),
    ]


@pytest.mark.parametrize(
    ("value", "hint"),
    [
        ("High", "eba_ZZ:x793"),  # label instead of code
        ("eba_zz:X793", "eba_ZZ:x793"),  # wrong case
        (" eba_ZZ:x793 ", "eba_ZZ:x793"),  # spaces: the code must be exact
        ("x793", None),  # no prefix: no guess
    ],
)
def test_dat_033_proposes_the_code_only_when_it_is_certain(value, hint):
    (message,) = run(**{"B_06.01": [function(impact=value)]})
    expected = f"#1 · {value!r}" + (f" → {hint}" if hint else "")
    assert message.details == expected


def test_dat_033_not_applicable_is_outside_list_l07():
    """#133: 'Not applicable' in B_05.01.0040 was the known non-compliance of the golden."""
    row = {"c0010": "P1", "c0020": "eba_qCO:qx2000", "c0030": "X", "c0040": "Not applicable"}
    (message,) = run(**{"B_05.01": [row]})
    assert message.params["column"].code == "B_05.01.0040"


# ------------------------------------------------------------------ documented exceptions
def test_hrk_is_outside_the_currencies_of_the_taxonomy():
    """PO, 30/10: the taxonomy prevails (P4); the EBA workbook still lists HRK."""
    (message,) = run(**{"B_02.01": [{"c0010": "C1", "c0020": "eba_CO:x1", "c0040": "eba_CU:HRK"}]})
    assert message.params["list"] == "L05"
    assert run(**{"B_02.01": [{"c0010": "C1", "c0020": "eba_CO:x1", "c0040": "eba_CU:EUR"}]}) == []


def test_not_applicable_country_only_where_the_taxonomy_allows_it():
    """eba_GA:qx2007 is in L10 (B_02.02.0130, 0150, 0160), not in L01 (B_02.02.0120)."""
    row = {"c0010": "C1", "c0120": "eba_GA:qx2007", "c0130": "eba_GA:qx2007"}
    (message,) = run(**{"B_02.02": [row]})
    assert message.params["column"].code == "B_02.02.0120"


def test_type_of_code_follows_the_taxonomy_not_the_rectified_its():
    """P4, RT-08: national code (qx2001) and passport (qx2005) are in L07, PNR and NIN are not."""
    codes = data_model.closed_lists()[("B_05.01", "c0020")].codes
    assert {"eba_qCO:qx2001", "eba_qCO:qx2005"} <= codes
    assert len(codes) == 6


# ------------------------------------------------------------------ origin and status
def test_severity_origin_and_status_follow_p3():
    registry = {e["code"]: e for e in load_registry()}
    assert load_catalog()["DAT-033"]["severity"] == "MAJOR"
    assert (registry["DAT-033"]["origin"], registry["DAT-033"]["severity_status"]) == (
        "OFFICIAL",
        "PROVISIONAL",
    )


# ------------------------------------------------------------------ provenance (RT-12)
SHA = re.compile(r"^[0-9a-f]{64}$")


def test_provenance_records_url_date_and_fingerprint():
    provenance = tool.load_provenance()
    assert provenance["lists"] == "enumerations-4.0.json"
    roles = {i["role"]: i for i in provenance["inputs"]}
    assert set(roles) == {"codes", "labels"}
    for source in roles.values():
        assert source["url"].startswith("https://www.eba.europa.eu/")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["published"])
        # RT-12 done (PO-37, 31/10): both sources carry a verified fingerprint.
        assert SHA.match(source["sha256"]), source["role"]
        assert source["status"].startswith("verified"), source["role"]
    assert roles["codes"]["sha256"] == (
        "27f3a44a6bdef56a7daf2114778707604c20b258e4466d5ebfb5c37b7598bad2"
    )


def test_the_kept_workbook_has_the_recorded_fingerprint():
    source = tool.labels_source()
    assert tool.sha256(tool.REFERENCE / source["local_copy"]) == source["sha256"]


def test_lists_are_fresh_against_the_workbook():
    """Every list of the EBA workbook equals a list of the JSON file, gaps documented apart."""
    assert tool.concordance(tool.REFERENCE / tool.labels_source()["local_copy"]) == []


def test_documented_gaps_are_still_real():
    """A gap that disappears (new workbook, new taxonomy) must be removed from the provenance."""
    workbook = tool.workbook_lists(tool.REFERENCE / tool.labels_source()["local_copy"])
    lists = json.loads(tool.ENUMERATIONS.read_text(encoding="utf-8"))["lists"]
    every_code = {v["code"] for lst in lists for v in lst["values"]}
    for gap in tool.load_provenance()["documented_gaps"]:
        sheets = [
            set(values)
            for (sheet, header), values in workbook.items()
            if header == gap["header"] and gap.get("sheet") in (None, sheet)
        ]
        assert sheets, gap["header"]
        for code in gap.get("only_in_workbook", []):
            assert code not in every_code and all(code in s for s in sheets), code
        for code in gap.get("only_in_taxonomy", []):
            assert code in every_code and all(code not in s for s in sheets), code


def test_the_tool_exits_cleanly(capsys):
    assert tool.main([]) == 0
    assert "SHA-256 ok, 0 undocumented difference(s)" in capsys.readouterr().out
