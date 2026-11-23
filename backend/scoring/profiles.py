# SPDX-License-Identifier: EUPL-1.2
"""Regulatory and expert profiles (Sprint 4, lot 1; decisions A1 and A2 of the PO, 02/11/2026).

Every check always runs. The profile is only a way of reading the findings, derived from the
origin of each code:

- REGULATORY: OFFICIAL (official texts and rules) and TECHNICAL (what makes a filing technically
  impossible to process);
- EXPERT: PO_VALIDATED and DATA_QUALITY, advice stricter than the official rules. An expert
  finding is never a regulatory non-compliance.
"""

from contracts.check_report import CheckDefinition, origin_of_code

REGULATORY = "REGULATORY"
EXPERT = "EXPERT"
PROFILES = (REGULATORY, EXPERT)

_BY_ORIGIN = {
    "OFFICIAL": REGULATORY,
    "TECHNICAL": REGULATORY,
    "PO_VALIDATED": EXPERT,
    "DATA_QUALITY": EXPERT,
}


def profile_of_origin(origin: str | None) -> str | None:
    """REGULATORY or EXPERT; None for an unknown origin (a code outside the registry)."""
    return _BY_ORIGIN.get(origin) if origin else None


def profile_of_code(code: str) -> str | None:
    return profile_of_origin(origin_of_code(code))


def profiles_of_check(definition: CheckDefinition) -> tuple[str, ...]:
    """Profiles of the codes of a check, in the order REGULATORY then EXPERT.

    A check may group codes of both profiles: its findings are then read code by code.
    """
    found = {profile_of_code(code) for code in definition.codes}
    return tuple(profile for profile in PROFILES if profile in found)
