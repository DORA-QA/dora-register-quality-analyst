# SPDX-License-Identifier: EUPL-1.2
"""Scores of an analysis (Sprint 4, lot 2; decision A4 of the PO, 02/11/2026).

The formula is unchanged since PO-10 (#13): each check weighs the seriousness of its most
serious code (BLOCKER 5, MAJOR 3, MINOR 1, INFO 1, ``SEVERITY_WEIGHT``); a passed check earns its
whole weight, a check that only warns earns half of it (``WARNING_CREDIT``), a failed check
earns nothing. A check that concerns the file but did not run, or could not read a column it
needs (« not evaluated »), earns nothing yet stays in the total, so a file that stops early
cannot look good. The score is the share of the weight earned, from 0 to 100, or None when no
check concerning the file ran at all (brief of the Sprint 4, §13: never an artificial 0).

The same formula is applied to two scopes:

- the regulatory score, on the REGULATORY codes only (OFFICIAL and TECHNICAL);
- the quality score, on every code (the « conformité experte » of the PO, 18/10/2026).

The confidence is 0 as soon as a check fails on a blocker, 100 when every check concerning the
file ran without a blocker, and « not evaluated » otherwise (variant decided in PO-10).
Provisional rules are counted at their severity; their number is returned so that the screen
can say it. These are internal quality indicators, without any regulatory value.
"""

import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass

from contracts.check_report import (
    SEVERITY_WEIGHT,
    CheckResult,
    CheckStatus,
    load_registry,
    origin_of_code,
)
from contracts.messages import Severity, load_catalog
from scoring.profiles import REGULATORY, profile_of_code

# Share of the weight earned by a check that only warns.
WARNING_CREDIT = 0.5
_CREDIT = {CheckStatus.PASSED: 1.0, CheckStatus.WARNING: WARNING_CREDIT, CheckStatus.FAILED: 0.0}
_NOT_DONE = (CheckStatus.SKIPPED, CheckStatus.NOT_EVALUATED)


@dataclass(frozen=True)
class CheckSummary:
    performed: int
    passed: int
    warnings: int
    failed: int
    # Quality score from 0 to 100 over all the checks, None when no check ran.
    score: int | None
    earned: float
    total: int
    # Confidence: 100 when no blocking check fails, 0 otherwise.
    confidence: int | None = None


def summarize(results: Iterable[CheckResult]) -> CheckSummary:
    """Scores over every check that ran (``summary`` of the API, formula of 0.8.0).

    DORA QA is free software with a single edition: every check runs and counts.
    """
    kept = list(results)
    done = [r for r in kept if r.status not in _NOT_DONE]
    # A check that concerns the file but did not run earns nothing, yet still counts in the total.
    total = sum(r.definition.weight for r in kept if r.applicable)
    earned = sum(r.definition.weight * _CREDIT[r.status] for r in done)
    return CheckSummary(
        performed=len(done),
        passed=sum(r.status is CheckStatus.PASSED for r in done),
        warnings=sum(r.status is CheckStatus.WARNING for r in done),
        failed=sum(r.status is CheckStatus.FAILED for r in done),
        score=round(100 * earned / total) if total else None,
        earned=earned,
        total=total,
        confidence=(
            (0 if any(r.status is CheckStatus.FAILED for r in done) else 100) if done else None
        ),
    )


def _severity(code: str) -> Severity:
    return Severity(load_catalog()[code]["severity"])


def restrict_to_profile(
    results: Iterable[CheckResult], profile: str, blind_codes: Iterable[str] = ()
) -> list[CheckResult]:
    """The results read through one profile: each check keeps only the codes of that profile.

    A check without any code of the profile is left out. The weight and the status of a kept
    check are recomputed on its remaining codes, with the rules of ``evaluate_checks``.
    """
    blind = set(blind_codes)
    restricted: list[CheckResult] = []
    for result in results:
        definition = result.definition
        codes = tuple(code for code in definition.codes if profile_of_code(code) == profile)
        if not codes:
            continue
        found = tuple(code for code in result.codes_found if code in codes)
        if result.status is CheckStatus.SKIPPED:
            status = CheckStatus.SKIPPED
        elif any(_severity(code) is Severity.BLOCKER for code in found):
            status = CheckStatus.FAILED
        elif found:
            status = CheckStatus.WARNING
        elif blind & set(codes):
            status = CheckStatus.NOT_EVALUATED
        else:
            status = CheckStatus.PASSED
        restricted.append(
            dataclasses.replace(
                result,
                definition=dataclasses.replace(
                    definition,
                    codes=codes,
                    weight=(
                        max(SEVERITY_WEIGHT[_severity(code)] for code in codes)
                        if definition.scored
                        else 0
                    ),
                    origins=tuple(dict.fromkeys(o for c in codes if (o := origin_of_code(c)))),
                ),
                status=status,
                codes_found=found,
            )
        )
    return restricted


@dataclass(frozen=True)
class ProfileScore:
    """A score and what it is made of, so that the reader can understand it (brief §11)."""

    scope: str  # REGULATORY or QUALITY
    value: int | None
    earned: float
    total: int
    performed: int
    passed: int
    warnings: int
    failed: int
    # Checks concerning the file that earned nothing because they did not run or are blind.
    not_run: tuple[str, ...]
    not_evaluated: tuple[str, ...]
    # Checks that do not concern the file (envelope checks on a ZIP): out of the total.
    not_applicable: tuple[str, ...]
    origins: tuple[str, ...]
    categories: tuple[str, ...]
    severities: tuple[str, ...]
    provisional_codes: int
    provisional_findings: int


def _provisional() -> frozenset[str]:
    return frozenset(e["code"] for e in load_registry() if e["severity_status"] == "PROVISIONAL")


def score_profile(results: Iterable[CheckResult], scope: str) -> ProfileScore:
    kept = list(results)
    summary = summarize(kept)
    codes = [code for r in kept for code in r.definition.codes]
    provisional = _provisional()
    return ProfileScore(
        scope=scope,
        # Brief §13: no check run means no score, never an artificial 0.
        value=summary.score if summary.performed else None,
        earned=summary.earned,
        total=summary.total,
        performed=summary.performed,
        passed=summary.passed,
        warnings=summary.warnings,
        failed=summary.failed,
        not_run=tuple(
            r.definition.id for r in kept if r.applicable and r.status is CheckStatus.SKIPPED
        ),
        not_evaluated=tuple(r.definition.id for r in kept if r.status is CheckStatus.NOT_EVALUATED),
        not_applicable=tuple(r.definition.id for r in kept if not r.applicable),
        origins=tuple(dict.fromkeys(o for r in kept for o in r.definition.origins)),
        categories=tuple(dict.fromkeys(r.definition.category for r in kept)),
        severities=tuple(s.value for s in Severity if any(_severity(code) is s for code in codes)),
        provisional_codes=sum(code in provisional for code in codes),
        provisional_findings=sum(code in provisional for r in kept for code in r.codes_found),
    )


@dataclass(frozen=True)
class Confidence:
    value: int | None
    # Checks concerning the file that did not run or could not read a column (PO-10 variant).
    not_run: tuple[str, ...]


def confidence(results: Iterable[CheckResult]) -> Confidence:
    """0 after a blocker; otherwise 100, or None (« not evaluated ») if a check did not run."""
    kept = list(results)
    if any(r.status is CheckStatus.FAILED for r in kept):
        return Confidence(0, ())
    not_run = tuple(r.definition.id for r in kept if r.applicable and r.status in _NOT_DONE)
    if not_run or not any(r.status not in _NOT_DONE for r in kept):
        return Confidence(None, not_run)
    return Confidence(100, ())


@dataclass(frozen=True)
class Scores:
    regulatory: ProfileScore
    quality: ProfileScore
    confidence: Confidence


def scores(results: Iterable[CheckResult], blind_codes: Iterable[str] = ()) -> Scores:
    every = list(results)
    return Scores(
        regulatory=score_profile(restrict_to_profile(every, REGULATORY, blind_codes), REGULATORY),
        quality=score_profile(every, "QUALITY"),
        confidence=confidence(every),
    )
