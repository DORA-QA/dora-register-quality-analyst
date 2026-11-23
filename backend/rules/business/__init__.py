# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3 rules: consistency between tables (REL), business rules (BUS), data quality (DQ)."""

from contracts.rules import IRule
from rules.business.amounts import amount_rules
from rules.business.arrangements import arrangement_rules
from rules.business.chains import chain_rules
from rules.business.entities import entity_rules
from rules.business.functions import function_rules
from rules.business.providers import provider_rules


def business_rules() -> list[IRule]:
    return [
        *entity_rules(),
        *provider_rules(),
        *arrangement_rules(),
        *function_rules(),
        *chain_rules(),
        *amount_rules(),
    ]
