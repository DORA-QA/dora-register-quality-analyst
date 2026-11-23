# SPDX-License-Identifier: EUPL-1.2
"""Interpreter of the EBA conditional rules (CL-2)."""

import pytest

from contracts import data_model
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import (
    Severity,
    field_label,
    fragment,
    has_blocker,
    render_fragment,
    render_message,
)
from rules.eba_conditional import (
    CodifiedRule,
    ComparisonRule,
    EbaConditionalRules,
    PresenceRule,
    compile_rule,
    compiled_rules,
    describe_condition,
    uninterpreted_rules,
)
from tests.test_technical_rules import frame


def run(tables):
    return EbaConditionalRules().evaluate(RoIDataset("ZIP", PackageMetadata(), tables))


def by_rule(messages):
    return {(m.params["rule"], m.code): m for m in messages}


# ------------------------------------------------------------------ coverage
def test_every_active_rule_is_interpreted_or_explicitly_delegated() -> None:
    active = {rule.id for rule in data_model.active_rules()}
    interpreted = {rule.rule_id for rule in compiled_rules()}
    assert len(active) == 49
    assert len(interpreted) == 45
    assert set(uninterpreted_rules()) == {"v8826_m", "v8890_m", "v8891_m", "v8892_m"}
    assert interpreted | set(uninterpreted_rules()) == active


def test_forms_are_counted() -> None:
    kinds = [type(rule) for rule in compiled_rules()]
    assert kinds.count(PresenceRule) == 40  # 3 dependencies + 37 groups (V8883 included)
    assert kinds.count(CodifiedRule) == 3
    assert kinds.count(ComparisonRule) == 2


def test_inactive_rules_are_never_interpreted() -> None:
    inactive = [r for r in data_model.rule_status().values() if not r.active]
    assert inactive
    assert {r.rule_id for r in compiled_rules()}.isdisjoint({r.id for r in inactive})


def test_rule_whose_columns_do_not_match_its_cells_is_not_interpreted() -> None:
    status = data_model.rule_status()["v8856_m"]
    assert compile_rule(status) is not None
    altered = data_model.RuleStatus(
        status.id, status.table, status.kind, True, True, status.expression, ("c0030", "c0090")
    )
    assert compile_rule(altered) is None


def test_unknown_form_is_not_guessed() -> None:
    status = data_model.RuleStatus(
        "vX_m",
        "B_01.02",
        "user_defined",
        True,
        True,
        "with {tB_01.02}: sum({c0110}) > 3",
        ("c0110",),
    )
    assert compile_rule(status) is None


def test_v8883_applies_the_intention_not_the_faulty_expression() -> None:
    (rule,) = [r for r in compiled_rules() if r.rule_id == "v8883_m"]
    assert rule.triggers == ("c0020", "c0030", "c0050", "c0060", "c0070", "c0080", "c0090")
    assert rule.target == "c0100"


# ---------------------------------------------------------------- presence
def test_dependency_requires_the_companion_value() -> None:
    tables = {"B_01.03": frame("B_01.03", {"c0010": "B1", "c0020": "L", "c0030": "Name"})}
    found = by_rule(run(tables))
    message = found[("V8856", "DAT-023")]
    assert message.params["column"] == field_label("B_01.03.0040")
    assert message.params["count"] == 1
    assert message.official_codes == ("EBA.V8856",)
    assert [(o.table, o.row, o.column) for o in message.occurrences] == [("B_01.03", 1, "c0040")]


def test_dependency_works_both_ways() -> None:
    tables = {"B_01.03": frame("B_01.03", {"c0010": "B1", "c0020": "L", "c0040": "eba_GA:FR"})}
    assert ("V8857", "DAT-023") in by_rule(run(tables))


def test_complete_row_and_empty_row_are_accepted() -> None:
    row = {"c0010": "B1", "c0020": "L", "c0030": "Name", "c0040": "eba_GA:FR"}
    empty = {"c0010": "B2", "c0020": "L"}
    assert run({"B_01.03": frame("B_01.03", row, empty)}) == []


def test_whitespace_counts_as_empty() -> None:
    tables = {"B_01.03": frame("B_01.03", {"c0010": "B1", "c0030": "Name", "c0040": "  "})}
    assert ("V8856", "DAT-023") in by_rule(run(tables))


def test_group_is_reported_once_per_rule_with_every_row() -> None:
    rows = [{"c0010": str(i), "c0020": "Name"} for i in range(3)]
    found = by_rule(run({"B_01.01": frame("B_01.01", *rows)}))
    message = found[("V8873", "DAT-023")]  # c0020 filled -> c0030 required
    assert message.params["count"] == 3
    assert [o.row for o in message.occurrences] == [1, 2, 3]
    assert message.params["form"] == "group"


def test_absent_table_or_column_is_ignored() -> None:
    assert run({}) == []
    assert run({"B_01.03": frame("B_01.03").drop("c0040")}) == []


def test_v8883_triggered_by_c0090() -> None:
    tables = {"B_06.01": frame("B_06.01", {"c0010": "F1", "c0090": "x"})}
    assert ("V8883", "DAT-023") in by_rule(run(tables))


# ---------------------------------------------------------- codified value
def test_codified_condition_requires_the_target() -> None:
    tables = {"B_02.01": frame("B_02.01", {"c0010": "C1", "c0020": "eba_CO:x3"})}
    message = by_rule(run(tables))[("V8805", "DAT-024")]
    assert message.params["column"] == field_label("B_02.01.0030")
    assert "(B_02.01.0020)" in str(render_fragment(message.params["condition"], "en"))


def test_codified_condition_not_met_gives_nothing() -> None:
    tables = {"B_02.01": frame("B_02.01", {"c0010": "C1", "c0020": "eba_CO:x1"})}
    assert ("V8805", "DAT-024") not in by_rule(run(tables))


def test_codified_comparison_ignores_case_and_spaces() -> None:
    tables = {"B_02.01": frame("B_02.01", {"c0010": "C1", "c0020": " EBA_co:X3 "})}
    assert ("V8805", "DAT-024") in by_rule(run(tables))


def test_null_condition_does_not_trigger_a_difference_rule() -> None:
    # V8804: c0040 != x318 and != x317 -> c0110 required. An empty c0040 does not apply.
    tables = {"B_01.02": frame("B_01.02", {"c0010": "L"})}
    assert ("V8804", "DAT-024") not in by_rule(run(tables))
    other = {"B_01.02": frame("B_01.02", {"c0010": "L", "c0040": "eba_CT:x12"})}
    assert ("V8804", "DAT-024") in by_rule(run(other))
    excluded = {"B_01.02": frame("B_01.02", {"c0010": "L", "c0040": "eba_CT:x318"})}
    assert ("V8804", "DAT-024") not in by_rule(run(excluded))


def test_or_condition_uses_either_member() -> None:
    for member in ("eba_ZZ:x959", "eba_ZZ:x960"):
        tables = {"B_07.01": frame("B_07.01", {"c0010": "C", "c0020": "P", "c0050": member})}
        assert ("V8825", "DAT-024") in by_rule(run(tables))


# ------------------------------------------------------------------ numeric
def test_negative_amount_is_reported() -> None:
    tables = {"B_01.02": frame("B_01.02", {"c0010": "L", "c0110": "-1", "c0100": "eba_CU:EUR"})}
    message = by_rule(run(tables))[("V22913", "DAT-026")]
    assert (message.params["operator"], message.params["constant"]) == (fragment("op_ge"), "0")
    assert message.occurrences[0].value == "-1"


def test_zero_and_positive_amounts_are_accepted() -> None:
    rows = [{"c0010": "L1", "c0110": "0"}, {"c0010": "L2", "c0110": "12.5"}]
    assert ("V22913", "DAT-026") not in by_rule(run({"B_01.02": frame("B_01.02", *rows)}))


def test_non_numeric_value_is_a_separate_finding() -> None:
    tables = {"B_02.01": frame("B_02.01", {"c0010": "C", "c0050": "12,5"})}
    found = by_rule(run(tables))
    assert ("V23716", "DAT-025") in found
    assert ("V23716", "DAT-026") not in found


def test_decimals_suffix_is_read_as_a_number() -> None:
    tables = {"B_02.01": frame("B_02.01", {"c0010": "C", "c0050": "-5d-2"})}
    found = by_rule(run(tables))
    assert ("V23716", "DAT-026") in found
    assert ("V23716", "DAT-025") not in found


# ----------------------------------------------------------------- findings
@pytest.mark.parametrize(
    ("code", "status"),
    [
        # Mandatory values (v88xx_m): no rejection by the ESAs (EBA observations, p. 3).
        ("DAT-023", "CONFIRMED"),
        ("DAT-024", "CONFIRMED"),
        # Numeric format: no source yet.
        ("DAT-025", "PROVISIONAL"),
        # Sign rule v22913: active, published as a warning by the EBA (PO-16, #84).
        ("DAT-026", "CONFIRMED"),
    ],
)
def test_findings_are_major_and_rendered_in_both_languages(code, status) -> None:
    tables = {
        "B_01.03": frame("B_01.03", {"c0010": "B1", "c0030": "N"}),
        "B_02.01": frame("B_02.01", {"c0010": "C", "c0020": "eba_CO:x3", "c0050": "abc"}),
        "B_01.02": frame("B_01.02", {"c0010": "L", "c0110": "-3"}),
    }
    message = next(m for m in run(tables) if m.code == code)
    assert not has_blocker([message])
    for language in ("en", "fr"):
        rendered = render_message(message, language)
        assert rendered.severity_status == status
        assert rendered.authority_code.startswith("EBA.V")
        assert "{" not in rendered.message


# ------------------------------------------------------------------ wording (#179)
def test_codified_finding_reads_with_labels_and_eba_severity() -> None:
    tables = {"B_07.01": frame("B_07.01", {"c0010": "C", "c0020": "P", "c0050": "eba_ZZ:x959"})}
    rendered = render_message(by_rule(run(tables))[("V8825", "DAT-024")], "en")
    assert "(B_07.01.0060) is empty" in rendered.message
    assert "(B_07.01.0050) is 'Not substitutable' or 'Highly complex substitutability'" in (
        rendered.message
    )
    assert "eba_ZZ" not in rendered.message
    assert rendered.eba_severity == "warning"
    assert rendered.severity is Severity.MAJOR


def test_not_equal_tests_on_one_column_are_merged() -> None:
    rule = next(r for r in compiled_rules() if r.rule_id.startswith("v8804"))
    text = str(render_fragment(describe_condition(rule), "fr"))
    assert text.count("(B_01.02.0040)") == 1
    assert "a une autre valeur que" in text
