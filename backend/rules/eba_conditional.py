# SPDX-License-Identifier: EUPL-1.2
"""Interpreter of the EBA conditional validation rules (CL-2).

The rules come from ``reference/dora/rule-status-4.0.json`` (official EBA list VR_4.4.phase1,
October 2026; same DORA content as the list of 14/09/2026). Only the
*active* rules are interpreted, and only four forms are understood; a rule written in any other
form is never guessed and produces nothing:

- presence dependency: ``if not isnull(A) then not isnull(B)``;
- completeness of a group: the same form with several triggers (``or``) for one target;
- numeric comparison with a constant: ``{c0110} >= 0``;
- presence conditioned by a codified value: ``if {c0040} != [eba_CT:x318] and ... then ...``.

Safeguards:

- the columns found in the expression must be the cells declared for the rule, otherwise the
  rule is not interpreted;
- an empty cell is "null": a condition on a null value is not met (the rule does not apply);
- V8883 has a faulty EBA expression (C0020 twice, C0090 omitted): the intention (C0020 to C0090
  trigger C0100) is applied instead;
- V8826, V8890, V8891 and V8892 are LEI masks, already covered by DAT-006 to DAT-010 on the same
  columns: they are delegated, not interpreted a second time.
"""

import re
from dataclasses import dataclass, replace
from typing import Literal

from contracts import data_model
from contracts.dataset import RoIDataset
from contracts.messages import (
    Fragment,
    Joined,
    Occurrence,
    ValidationMessage,
    field_label,
    fragment,
    make_message,
    member_label,
    with_occurrences,
)
from contracts.naming import field_reference
from rules.technical.locations import describe
from rules.technical.numbers import DECIMALS_SUFFIX

ROW_COLUMN = "_row"
PRESENCE_CODE = "DAT-023"
CODIFIED_CODE = "DAT-024"
NOT_NUMERIC_CODE = "DAT-025"
COMPARISON_CODE = "DAT-026"

# LEI masks, handled by the LEI checks (DAT-006 to DAT-010).
DELEGATED_TO_LEI_CHECKS = frozenset({"v8826_m", "v8890_m", "v8891_m", "v8892_m"})
# Faulty EBA expressions, replaced by the intention confirmed by the Product Owner (PO-6).
CORRECTED_TRIGGERS = {
    "v8883_m": ("c0020", "c0030", "c0050", "c0060", "c0070", "c0080", "c0090"),
}

_HEADER = re.compile(r"^with\s*\{t(?P<table>[A-Z]_\d{2}\.\d{2})\b[^}]*\}\s*:\s*(?P<body>.+)$", re.S)
_COLUMN = re.compile(r"\{(c\d{4})\}")
_CONDITIONAL = re.compile(r"^if\s*(?P<cond>.+?)\s*then\s*(?P<then>.+?)\s*endif$", re.S)
_COMPARISON = re.compile(r"^\{(c\d{4})\}\s*(>=|<=|>|<|!=|=)\s*(-?\d+(?:\.\d+)?)$")
_NOT_NULL = re.compile(r"not[\s(]*isnull\s*\(\s*\{(c\d{4})\}\s*\)")
_EQUALITY = re.compile(r"\{(c\d{4})\}\s*(!=|=)\s*\[([^\]]+)\]")
# How each operator is written in the texts (#179).
OPERATOR_FRAGMENTS = {
    ">=": "op_ge",
    "<=": "op_le",
    ">": "op_gt",
    "<": "op_lt",
    "=": "op_eq",
    "!=": "op_ne",
}
_OPERATORS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass(frozen=True)
class PresenceRule:
    rule_id: str
    table: str
    triggers: tuple[str, ...]
    target: str
    form: Literal["dependency", "group"]


@dataclass(frozen=True)
class CodifiedRule:
    rule_id: str
    table: str
    tests: tuple[tuple[str, str, str], ...]  # (column, operator, member)
    joiner: Literal["and", "or"]
    target: str


@dataclass(frozen=True)
class ComparisonRule:
    rule_id: str
    table: str
    column: str
    operator: str
    constant: float


CompiledRule = PresenceRule | CodifiedRule | ComparisonRule


def _squash(text: str) -> str:
    return " ".join(text.split())


def compile_rule(status: data_model.RuleStatus) -> CompiledRule | None:
    """Understand one rule, or return None when it is outside the four known forms."""
    if status.id in DELEGATED_TO_LEI_CHECKS:
        return None
    header = _HEADER.match(_squash(status.expression))
    if not header:
        return None
    table, body = header["table"], header["body"].strip()
    columns = set(_COLUMN.findall(body))
    if status.id not in CORRECTED_TRIGGERS and columns != set(status.cells):
        return None

    comparison = _COMPARISON.match(body)
    if comparison:
        column, operator, constant = comparison.groups()
        return ComparisonRule(status.id, table, column, operator, float(constant))

    conditional = _CONDITIONAL.match(body)
    if not conditional:
        return None
    then = _NOT_NULL.findall(conditional["then"])
    if len(then) != 1 or re.sub(r"[()\s]", "", _NOT_NULL.sub("", conditional["then"])):
        return None
    target = then[0]
    cond = conditional["cond"].strip()

    present = _NOT_NULL.findall(cond)
    remainder = _NOT_NULL.sub("", cond)
    if present and not re.sub(r"[()\s]|\bor\b", "", remainder):
        triggers = tuple(dict.fromkeys(present))
        if status.id in CORRECTED_TRIGGERS:
            triggers = CORRECTED_TRIGGERS[status.id]
        form: Literal["dependency", "group"] = "dependency" if len(triggers) == 1 else "group"
        return PresenceRule(status.id, table, triggers, target, form)

    tests = tuple(_EQUALITY.findall(cond))
    leftover = _EQUALITY.sub("", cond)
    joiners = {word for word in re.findall(r"\b(and|or)\b", leftover)}
    if tests and not re.sub(r"[()\s]|\b(and|or)\b", "", leftover) and len(joiners) <= 1:
        joiner: Literal["and", "or"] = "or" if joiners == {"or"} else "and"
        return CodifiedRule(status.id, table, tests, joiner, target)
    return None


def compiled_rules() -> list[CompiledRule]:
    """The active rules that the interpreter understands, in the order of the EBA list."""
    found = (compile_rule(status) for status in data_model.active_rules())
    return [rule for rule in found if rule is not None]


def uninterpreted_rules() -> list[str]:
    """Active rules that produce nothing here (delegated or outside the four forms)."""
    interpreted = {rule.rule_id for rule in compiled_rules()}
    return [s.id for s in data_model.active_rules() if s.id not in interpreted]


# ------------------------------------------------------------------ evaluation
def _is_null(value: object) -> bool:
    return value is None or not str(value).strip()


def _member(value: str) -> str:
    return value.strip().lower()


def _official(rule_id: str) -> str:
    return "EBA." + rule_id.split("_")[0].upper()


def _short(rule_id: str) -> str:
    return rule_id.split("_")[0].upper()


def _finding(
    code: str,
    rule_id: str,
    table: str,
    hits: list[tuple[int, str, str | None]],
    **params: object,
) -> ValidationMessage:
    """One finding per rule and table: ``hits`` are (row, column, value)."""
    lines = [f"#{row} · {field_reference(table, column)}" for row, column, _ in hits]
    message = make_message(
        code,
        details=describe(lines),
        rule=_short(rule_id),
        table=table,
        count=len(hits),
        **params,
    )
    message = replace(message, official_codes=(_official(rule_id),))
    return with_occurrences(
        message,
        [
            Occurrence(table=table, row=row, column=column, value=value)
            for row, column, value in hits
        ],
        total=len(hits),
    )


def _rows(dataset: RoIDataset, table: str, columns: tuple[str, ...]):
    frame = dataset.tables.get(table)
    if frame is None or any(column not in frame.columns for column in columns):
        return None
    return frame.select([ROW_COLUMN, *columns]).iter_rows(named=True)


def _evaluate_presence(rule: PresenceRule, dataset: RoIDataset) -> list[ValidationMessage]:
    rows = _rows(dataset, rule.table, (*rule.triggers, rule.target))
    if rows is None:
        return []
    hits = [
        (row[ROW_COLUMN], rule.target, None)
        for row in rows
        if any(not _is_null(row[c]) for c in rule.triggers) and _is_null(row[rule.target])
    ]
    if not hits:
        return []
    return [
        _finding(
            PRESENCE_CODE,
            rule.rule_id,
            rule.table,
            hits,
            column=field_label(field_reference(rule.table, rule.target)),
            triggers=Joined(
                tuple(field_label(field_reference(rule.table, c)) for c in rule.triggers), "or"
            ),
            form=rule.form,
        )
    ]


def _condition_met(rule: CodifiedRule, row: dict) -> bool:
    outcomes = []
    for column, operator, member in rule.tests:
        value = row[column]
        if _is_null(value):
            return False  # null condition: the rule does not apply
        same = _member(str(value)) == _member(member)
        outcomes.append(same if operator == "=" else not same)
    return all(outcomes) if rule.joiner == "and" else any(outcomes)


def describe_condition(rule: CodifiedRule) -> Joined:
    """The condition of a rule, in words: column labels and list labels (PO, #179).

    Consecutive tests on the same column are merged: "= A or = B" reads "is A or B",
    "≠ A and ≠ B" reads "is other than A or B".
    """
    groups: list[tuple[str, str, list[str]]] = []
    merges = (rule.joiner == "or" and "=") or (rule.joiner == "and" and "!=")
    for column, operator, member in rule.tests:
        if groups and groups[-1][0] == column and groups[-1][1] == operator == merges:
            groups[-1][2].append(member)
        else:
            groups.append((column, operator, [member]))
    tests: list[Fragment] = [
        fragment(
            "test_equal" if operator == "=" else "test_not_equal",
            column=field_label(field_reference(rule.table, column)),
            members=Joined(tuple(member_label(m) for m in members), "or"),
        )
        for column, operator, members in groups
    ]
    return Joined(tuple(tests), rule.joiner)


def _evaluate_codified(rule: CodifiedRule, dataset: RoIDataset) -> list[ValidationMessage]:
    tested = tuple(dict.fromkeys(column for column, _, _ in rule.tests))
    rows = _rows(dataset, rule.table, (*tested, rule.target))
    if rows is None:
        return []
    hits = [
        (row[ROW_COLUMN], rule.target, None)
        for row in rows
        if _condition_met(rule, row) and _is_null(row[rule.target])
    ]
    if not hits:
        return []
    return [
        _finding(
            CODIFIED_CODE,
            rule.rule_id,
            rule.table,
            hits,
            column=field_label(field_reference(rule.table, rule.target)),
            condition=describe_condition(rule),
        )
    ]


def _parse_number(value: str) -> float | None:
    text = value.strip()
    if DECIMALS_SUFFIX.search(text):
        text = text[: text.lower().rindex("d")]  # the suffix is reported by DAT-015
    try:
        return float(text)
    except ValueError:
        return None


def _evaluate_comparison(rule: ComparisonRule, dataset: RoIDataset) -> list[ValidationMessage]:
    rows = _rows(dataset, rule.table, (rule.column,))
    if rows is None:
        return []
    not_numeric: list[tuple[int, str, str | None]] = []
    violations: list[tuple[int, str, str | None]] = []
    for row in rows:
        value = row[rule.column]
        if _is_null(value):
            continue
        number = _parse_number(str(value))
        if number is None:
            not_numeric.append((row[ROW_COLUMN], rule.column, str(value)))
        elif not _OPERATORS[rule.operator](number, rule.constant):
            violations.append((row[ROW_COLUMN], rule.column, str(value)))
    column = field_label(field_reference(rule.table, rule.column))
    constant = f"{rule.constant:g}"
    messages = []
    if not_numeric:
        messages.append(
            _finding(NOT_NUMERIC_CODE, rule.rule_id, rule.table, not_numeric, column=column)
        )
    if violations:
        messages.append(
            _finding(
                COMPARISON_CODE,
                rule.rule_id,
                rule.table,
                violations,
                column=column,
                operator=fragment(OPERATOR_FRAGMENTS[rule.operator]),
                constant=constant,
            )
        )
    return messages


class EbaConditionalRules:
    """Runs every active, understood EBA conditional rule on the dataset."""

    id = "EBA_CONDITIONAL"

    def __init__(self, rules: list[CompiledRule] | None = None) -> None:
        self._rules = compiled_rules() if rules is None else rules

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        for rule in self._rules:
            if isinstance(rule, PresenceRule):
                messages += _evaluate_presence(rule, dataset)
            elif isinstance(rule, CodifiedRule):
                messages += _evaluate_codified(rule, dataset)
            else:
                messages += _evaluate_comparison(rule, dataset)
        return messages
