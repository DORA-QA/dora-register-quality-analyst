# SPDX-License-Identifier: EUPL-1.2
"""Technical checks on the data: header, presence, primary and foreign keys."""

import json

import polars as pl
import pytest

from contracts import data_model
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import Severity
from rules.engine import RulesEngine
from rules.technical import technical_rules
from rules.technical.keys import ForeignKeyRule


def frame(table: str, *rows: dict[str, str], extra: tuple[str, ...] = ()) -> pl.DataFrame:
    columns = [*data_model.tables()[table].columns, *extra]
    data = {c: [r.get(c, "") for r in rows] for c in columns}
    data["_row"] = list(range(1, len(rows) + 1))
    return pl.DataFrame(data, schema={**dict.fromkeys(columns, pl.Utf8), "_row": pl.Int64})


KEY_CODES = {"DAT-001", "DAT-002", "DAT-003", "DAT-004", "DAT-005"}


def run_all(tables: dict[str, pl.DataFrame]):
    return RulesEngine(technical_rules()).run(RoIDataset("ZIP", PackageMetadata(), tables)).messages


def run(tables: dict[str, pl.DataFrame]):
    """Findings of the header, presence and key rules (identifier checks have their own tests)."""
    return [m for m in run_all(tables) if m.code in KEY_CODES]


def codes(messages) -> list[str]:
    return sorted(m.code for m in messages)


ENTITY = {"c0010": "ENTITY00000000000001"}


def test_reference_covers_every_foreign_key_of_the_taxonomy() -> None:
    fields = json.loads((data_model.REFERENCE_DIR / "fields-4.0.json").read_text(encoding="utf-8"))[
        "fields"
    ]
    expected = {f["code"] for f in fields if f["references"]}
    covered = {
        f"{c.source_table}.{col[1:]}"
        for c in data_model.key_constraints()
        for col in c.source_columns
    }
    assert covered == expected
    model = data_model.tables()
    for c in data_model.key_constraints():
        assert set(c.source_columns) <= set(model[c.source_table].columns), c.id
        assert set(c.target_columns) <= set(model[c.target_table].columns), c.id
        assert len(c.source_columns) == len(c.target_columns), c.id


def test_primary_keys_follow_the_data_model() -> None:
    model = data_model.tables()
    assert model["B_01.01"].primary_key == ("c0010",)
    assert model["B_06.01"].primary_key == ("c0010", "c0040")
    assert len(model["B_02.02"].primary_key) == 8


def test_a_clean_package_has_no_finding() -> None:
    tables = {
        "B_01.01": frame("B_01.01", ENTITY),
        "B_01.02": frame("B_01.02", ENTITY),
        "B_02.01": frame("B_02.01", {"c0010": "CONTRACT1"}),
    }
    assert run(tables) == []


def test_unknown_header_codes_are_listed() -> None:
    tables = {"B_01.01": frame("B_01.01", ENTITY, extra=("c0999", "C0010"))}

    [message] = run(tables)

    assert message.code == "DAT-001"
    assert message.severity is Severity.BLOCKER
    assert message.params == {"table": "B_01.01", "count": 2}
    assert message.details == "c0999\nC0010"
    assert message.official_codes == ("EBA.801",)


def test_an_empty_reporting_entity_table_is_blocking() -> None:
    [message] = run({"B_01.01": frame("B_01.01")})

    assert (message.code, message.severity) == ("DAT-002", Severity.BLOCKER)
    # Other tables may legitimately be empty.
    assert run({"B_01.02": frame("B_01.02")}) == []


def test_missing_primary_key_values_are_located() -> None:
    tables = {"B_01.02": frame("B_01.02", ENTITY, {"c0010": ""}, {"c0010": "ENTITY00000000000003"})}

    [message] = run(tables)

    assert message.code == "DAT-003"
    assert message.params["count"] == 1
    assert message.details == "#2 · B_01.02.0010"


def test_a_primary_key_column_left_out_reports_every_row() -> None:
    table = frame("B_01.02", ENTITY, {"c0010": "ENTITY00000000000002"}).drop("c0010")

    [message] = run({"B_01.02": table})

    assert message.code == "DAT-003"
    assert message.params["count"] == 2


def test_duplicate_keys_are_reported_from_the_second_occurrence() -> None:
    tables = {"B_01.02": frame("B_01.02", ENTITY, {"c0010": "OTHER"}, ENTITY, ENTITY)}

    [message] = run(tables)

    assert (message.code, message.severity) == ("DAT-004", Severity.MAJOR)
    assert message.params["count"] == 2
    assert message.details == "#3 · ENTITY00000000000001\n#4 · ENTITY00000000000001"


def test_composite_keys_must_be_unique_as_a_whole() -> None:
    a = {"c0010": "C1", "c0020": "P1"}
    b = {"c0010": "C1", "c0020": "P2"}

    assert [m for m in run({"B_03.02": frame("B_03.02", a, b)}) if m.code == "DAT-004"] == []
    assert codes(run({"B_03.02": frame("B_03.02", a, b, a)})) == ["DAT-004"]


def test_foreign_key_to_a_missing_record_is_blocking() -> None:
    tables = {
        "B_02.01": frame("B_02.01", {"c0010": "CONTRACT1"}),
        "B_03.01": frame(
            "B_03.01", {"c0010": "CONTRACT1", "c0020": "E1"}, {"c0010": "UNKNOWN", "c0020": "E1"}
        ),
        "B_01.02": frame("B_01.02", {"c0010": "E1"}),
    }

    [message] = run(tables)

    assert (message.code, message.severity) == ("DAT-005", Severity.BLOCKER)
    assert message.params["table"] == "B_03.01"
    assert message.params["constraint"] == "R10"
    assert message.params["target"] == "B_02.01.0010"
    assert message.details == "#2 · UNKNOWN"


def test_foreign_keys_ignore_empty_values_and_missing_target_tables() -> None:
    nullable = {"B_02.01": frame("B_02.01", {"c0010": "C1", "c0030": ""})}
    assert run(nullable) == []
    # The target table did not load: the import steps report it, not this rule.
    assert run({"B_03.01": frame("B_03.01", {"c0010": "X", "c0020": "Y"})}) == []


def test_composite_foreign_key_compares_the_pair() -> None:
    tables = {
        "B_03.02": frame("B_03.02", {"c0010": "C1", "c0020": "P1"}),
        "B_02.02": frame("B_02.02", {"c0010": "C1", "c0030": "P2"}),
    }

    messages = [m for m in run(tables) if m.code == "DAT-005"]

    assert [m.params["constraint"] for m in messages] == ["R17"]
    assert messages[0].details == "#1 · C1 | P2"


def test_keys_are_compared_exactly() -> None:
    tables = {
        "B_01.02": frame("B_01.02", {"c0010": "ENTITY1"}),
        "B_06.01": frame("B_06.01", {"c0010": "F1", "c0040": "entity1 "}),
    }

    assert codes(run(tables)) == ["DAT-005"]


def test_findings_are_capped_but_counted() -> None:
    rows = [{"c0010": ""} for _ in range(60)]

    [message] = run({"B_01.02": frame("B_01.02", *rows)})

    assert message.params["count"] == 60
    assert message.details is not None
    assert message.details.endswith("… (+35)")


def _constraint_tables(constraint, reference: str) -> dict[str, pl.DataFrame]:
    """Minimal tables for one constraint: the source cites ``reference``, the target has TARGET."""
    source = dict.fromkeys(constraint.source_columns, reference)
    target = dict.fromkeys(constraint.target_columns, "TARGET")
    if constraint.source_table == constraint.target_table:  # self-reference (R6, R13...)
        return {constraint.source_table: frame(constraint.source_table, {**target, **source})}
    return {
        constraint.source_table: frame(constraint.source_table, source),
        constraint.target_table: frame(constraint.target_table, target),
    }


@pytest.mark.parametrize("constraint", data_model.key_constraints(), ids=lambda c: c.id)
def test_every_foreign_key_constraint_is_enforced(constraint) -> None:
    """Brief §15: each of the 22 constraints (24 source columns) is checked, one by one."""
    rule = ForeignKeyRule()

    def fired(reference: str) -> list[str]:
        dataset = RoIDataset("ZIP", PackageMetadata(), _constraint_tables(constraint, reference))
        return [m.params["constraint"] for m in rule.evaluate(dataset)]

    assert constraint.id in fired("ORPHAN")
    assert constraint.id not in fired("TARGET")


def test_there_are_22_constraints_on_24_source_columns() -> None:
    constraints = data_model.key_constraints()
    assert len(constraints) == 22
    assert sum(len(c.source_columns) for c in constraints) == 24
