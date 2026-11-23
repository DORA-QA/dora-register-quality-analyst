# SPDX-License-Identifier: EUPL-1.2
"""A check whose rule lacks a column is "not evaluated", never "passed" (red team RT-09)."""

import ast
import re
from pathlib import Path

import polars as pl
from fastapi.testclient import TestClient

from api.main import app
from contracts.check_report import CheckStatus, evaluate_checks
from contracts.dataset import PackageMetadata, RoIDataset
from rules.business import business_rules
from rules.engine import RulesEngine
from scoring import summarize
from tests.cases.golden import load_golden
from tests.cases.mutations import drop_column
from tests.factories import CLIENT_HEADERS

RULES_DIR = Path(__file__).resolve().parent.parent / "rules" / "business"
CODE = re.compile(r"^[A-Z]{2,4}-\d{3}$")


def _frame(**columns) -> pl.DataFrame:
    rows = len(next(iter(columns.values())))
    return pl.DataFrame({"_row": list(range(1, rows + 1)), **columns})


def test_the_engine_records_the_columns_a_rule_could_not_read():
    dataset = RoIDataset(
        "ZIP",
        PackageMetadata(),
        {
            # c0050 (criticality) is missing from B_06.01.
            "B_06.01": _frame(c0010=["F1"], c0040=["LEI"]),
            "B_02.02": _frame(c0010=["C1"], c0020=["LEI"], c0050=["F1"]),
        },
    )
    result = RulesEngine(business_rules()).run(dataset)
    assert "B_06.01.c0050" in result.blind["REL-012"]
    assert {"REL-012", "DQ-011"} <= result.blind_codes


def test_complete_tables_leave_no_rule_blind():
    result = RulesEngine(business_rules()).run(RoIDataset("ZIP", PackageMetadata(), {}))
    assert result.blind == {} and result.blind_codes == set()


def test_a_blind_check_without_finding_is_not_evaluated_and_earns_nothing():
    steps = {"technical_rules": "OK", "dataset": "OK"}
    results = evaluate_checks([], steps, "ZIP", blind_codes={"REL-012"})
    by_id = {r.definition.id: r for r in results}
    assert by_id["rel_function_coverage"].status is CheckStatus.NOT_EVALUATED
    summary = summarize(results)
    clean = summarize(evaluate_checks([], steps, "ZIP"))
    assert summary.performed == clean.performed - 1
    assert summary.earned < clean.earned and summary.total == clean.total


def test_a_column_removed_from_the_golden_makes_its_checks_not_evaluated():
    package = load_golden()
    drop_column(package, "B_06.01", "c0050")
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        body = client.post("/api/import", files={"file": (package.name, package.to_zip())}).json()
    status = {check["id"]: check["status"] for check in body["checks"]}
    assert "DAT-030" in {m["code"] for m in body["messages"]}
    assert status["rel_function_coverage"] == "NOT_EVALUATED"
    assert status["rel_critical_services"] == "NOT_EVALUATED"


def test_the_golden_has_no_check_not_evaluated():
    package = load_golden()
    with TestClient(app, headers=CLIENT_HEADERS) as client:
        body = client.post("/api/import", files={"file": (package.name, package.to_zip())}).json()
    assert "NOT_EVALUATED" not in {check["status"] for check in body["checks"]}


def test_each_business_rule_declares_the_codes_it_emits():
    """The declaration drives RT-09: a code missing from it would read "passed" by mistake."""
    for path in sorted(RULES_DIR.glob("*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.ClassDef) or not any(
                isinstance(item, ast.FunctionDef) and item.name == "evaluate" for item in node.body
            ):
                continue
            written = {
                n.value
                for n in ast.walk(node)
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and CODE.match(n.value)
            }
            declared = next(
                rule.codes for rule in business_rules() if type(rule).__name__ == node.name
            )
            assert set(declared) == written, (path.name, node.name)
