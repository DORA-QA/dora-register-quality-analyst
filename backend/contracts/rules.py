# SPDX-License-Identifier: EUPL-1.2
"""Contract of a rule (technical checks of Sprint 2, business rules of Sprint 3).

A rule reads the dataset and returns findings. It never changes the dataset and
never reads anything but the dataset and the reference data.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from contracts.dataset import RoIDataset
from contracts.messages import ValidationMessage


class IRule(Protocol):
    """One rule. ``id`` is stable and appears in logs and documentation."""

    id: str

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]: ...


@dataclass
class RulesResult:
    messages: list[ValidationMessage] = field(default_factory=list)
    rules_run: int = 0
    # Rule id -> columns it read that the file does not have: its check is "not evaluated".
    blind: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # Codes those rules may emit (their ``codes`` attribute, else their id).
    blind_codes: set[str] = field(default_factory=set)


class IRulesEngine(Protocol):
    def run(self, dataset: RoIDataset) -> RulesResult: ...


def rules_of(engine_rules: Sequence[IRule]) -> list[str]:
    return [rule.id for rule in engine_rules]
