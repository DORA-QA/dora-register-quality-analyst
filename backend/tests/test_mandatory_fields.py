# SPDX-License-Identifier: EUPL-1.2
"""DAT-032: mandatory fields that no active EBA rule checks (PO-32, #121)."""

from contracts import data_model
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import Severity, has_blocker
from rules.technical.mandatory import UncoveredMandatoryFieldRule, uncovered_mandatory_fields
from tests.test_technical_rules import frame


def run(tables):
    return UncoveredMandatoryFieldRule().evaluate(RoIDataset("ZIP", PackageMetadata(), tables))


def test_the_uncovered_fields_are_computed_from_the_references() -> None:
    """The 41 mandatory fields minus the targets of the active rules: the two named by the PO."""
    assert len(data_model.mandatory_fields()) == 41
    assert uncovered_mandatory_fields() == (("B_04.01", "c0030"), ("B_07.01", "c0090"))


def test_an_empty_mandatory_field_is_a_major_located_finding() -> None:
    rows = [{"c0090": "eba_BT:x1"}, {"c0090": ""}, {"c0090": "  "}]
    messages = run({"B_07.01": frame("B_07.01", *rows)})

    assert [m.code for m in messages] == ["DAT-032"]
    message = messages[0]
    assert message.severity is Severity.MAJOR and not has_blocker(messages)
    assert message.params["column"] == "B_07.01.0090" and message.params["count"] == 2
    assert [(o.table, o.row, o.column) for o in message.occurrences] == [
        ("B_07.01", 2, "c0090"),
        ("B_07.01", 3, "c0090"),
    ]


def test_each_table_gets_its_own_finding() -> None:
    tables = {
        "B_04.01": frame("B_04.01", {"c0030": ""}),
        "B_07.01": frame("B_07.01", {"c0090": ""}),
    }
    places = sorted(m.params["column"] for m in run(tables))

    assert places == ["B_04.01.0030", "B_07.01.0090"]


def test_filled_fields_empty_tables_and_missing_columns_say_nothing() -> None:
    filled = {"B_04.01": frame("B_04.01", {"c0030": "eba_ZZ:x838"})}
    empty_table = {"B_07.01": frame("B_07.01")}
    no_column = {"B_07.01": frame("B_07.01", {"c0090": ""}).drop("c0090")}

    assert run(filled) == []
    assert run(empty_table) == []
    # A column missing from the header is DAT-030's finding.
    assert run(no_column) == []
    assert run({}) == []
