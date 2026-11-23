# SPDX-License-Identifier: EUPL-1.2
"""Runs a list of rules on a dataset.

A rule that fails does not stop the analysis: the other rules still run, and the
report says which rule could not run (ENG-001), so that a missing finding is never
read as compliance. The log names the rule and the type of error only, never the
error text, which may quote a value of the register.
"""

import logging
from collections.abc import Sequence

from contracts.dataset import RoIDataset
from contracts.messages import make_message
from contracts.rules import IRule, RulesResult
from contracts.tables import recording_missing_columns
from rules.business import business_rules
from rules.eba_conditional import EbaConditionalRules
from rules.technical import technical_rules

logger = logging.getLogger("roi.rules")
RULE_FAILED_CODE = "ENG-001"


class RulesEngine:
    def __init__(self, rules: Sequence[IRule] | None = None, extra: Sequence[IRule] = ()) -> None:
        self._rules = list(
            [*technical_rules(), EbaConditionalRules(), *business_rules()]
            if rules is None
            else rules
        )
        # Rules that need reference data given by the caller (GLEIF copy, branch gleif-local).
        self._rules += list(extra)

    def run(self, dataset: RoIDataset) -> RulesResult:
        result = RulesResult()
        for rule in self._rules:
            rule_id = getattr(rule, "id", type(rule).__name__)
            with recording_missing_columns() as missing:
                try:
                    found = rule.evaluate(dataset)
                except Exception as error:  # noqa: BLE001 - one rule must not stop the others
                    logger.error("rule %s failed: %s", rule_id, type(error).__name__)
                    found = [make_message(RULE_FAILED_CODE, rule=rule_id)]
            if missing:
                # RT-09: the rule could not read every column it needs (DAT-030 names them).
                result.blind[rule_id] = tuple(f"{t}.{c}" for t, c in sorted(missing))
                result.blind_codes.update(getattr(rule, "codes", (rule_id,)))
            skipped = tuple(getattr(rule, "skipped_codes", ()))
            if skipped:
                # The rule had no reference data to compare with (no GLEIF copy installed).
                result.blind[rule_id] = ("reference data",)
                result.blind_codes.update(skipped)
            result.messages.extend(found)
            result.rules_run += 1
        return result
