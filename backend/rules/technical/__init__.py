# SPDX-License-Identifier: EUPL-1.2
"""Technical checks on the data (Sprint 2): header, presence, keys."""

from contracts.rules import IRule
from rules.technical.enumerations import ClosedListRule
from rules.technical.headers import MissingColumnsRule, UnknownColumnsRule
from rules.technical.identifier_types import IdentifierTypeRule
from rules.technical.identifiers import EuidRule, LeiRule
from rules.technical.keys import (
    ConditionalKeyRule,
    DuplicateKeyRule,
    ForeignKeyRule,
    FrameworkContractTypeRule,
    MissingKeyRule,
)
from rules.technical.lengths import MaxLengthRule
from rules.technical.mandatory import UncoveredMandatoryFieldRule
from rules.technical.numbers import NumericSuffixRule
from rules.technical.presence import ReportingEntityPresentRule


def technical_rules() -> list[IRule]:
    return [
        UnknownColumnsRule(),
        MissingColumnsRule(),
        ReportingEntityPresentRule(),
        MissingKeyRule(),
        ConditionalKeyRule(),
        DuplicateKeyRule(),
        ForeignKeyRule(),
        FrameworkContractTypeRule(),
        LeiRule(),
        EuidRule(),
        IdentifierTypeRule(),
        NumericSuffixRule(),
        MaxLengthRule(),
        ClosedListRule(),
        UncoveredMandatoryFieldRule(),
    ]
