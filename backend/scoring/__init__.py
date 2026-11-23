# SPDX-License-Identifier: EUPL-1.2
"""Scoring engine: profiles and scores computed from the results of the checks.

The formula lives here and only here (brief of the Sprint 4, §11): the frontend shows what the
API returns and never computes a score itself. The formula is described in ``docs/scores.md``.
"""

from scoring.profiles import (
    EXPERT,
    PROFILES,
    REGULATORY,
    profile_of_code,
    profile_of_origin,
    profiles_of_check,
)
from scoring.scores import (
    WARNING_CREDIT,
    CheckSummary,
    Confidence,
    ProfileScore,
    Scores,
    confidence,
    restrict_to_profile,
    score_profile,
    scores,
    summarize,
)

__all__ = [
    "EXPERT",
    "PROFILES",
    "REGULATORY",
    "WARNING_CREDIT",
    "CheckSummary",
    "Confidence",
    "ProfileScore",
    "Scores",
    "confidence",
    "profile_of_code",
    "profile_of_origin",
    "profiles_of_check",
    "restrict_to_profile",
    "score_profile",
    "scores",
    "summarize",
]
