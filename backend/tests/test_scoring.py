# SPDX-License-Identifier: EUPL-1.2
"""Profiles and scores (Sprint 4, lots 1 and 2; decisions A1, A2 and A4 of the PO, 02/11/2026)."""

import pytest

from contracts.check_report import CheckStatus, evaluate_checks, load_checks, load_registry
from contracts.messages import load_catalog, make_message
from scoring import (
    EXPERT,
    REGULATORY,
    confidence,
    profile_of_code,
    profile_of_origin,
    profiles_of_check,
    restrict_to_profile,
    scores,
    summarize,
)
from tests.test_check_report import ALL_RAN


# ------------------------------------------------------------------ profiles
@pytest.mark.parametrize(
    ("origin", "profile"),
    [
        ("OFFICIAL", REGULATORY),
        ("TECHNICAL", REGULATORY),  # A1: a filing that cannot be processed is not an opinion
        ("PO_VALIDATED", EXPERT),
        ("DATA_QUALITY", EXPERT),
        (None, None),
        ("UNKNOWN", None),
    ],
)
def test_profile_of_origin(origin, profile) -> None:
    assert profile_of_origin(origin) == profile


def test_every_code_of_the_catalogue_has_a_profile() -> None:
    assert [code for code in load_catalog() if profile_of_code(code) is None] == []


def test_profile_follows_the_origin_of_the_registry() -> None:
    for entry in load_registry():
        assert profile_of_code(entry["code"]) == profile_of_origin(entry["origin"]), entry["code"]


def test_a_check_mixing_origins_holds_both_profiles() -> None:
    check = next(c for c in load_checks() if c.id == "data_additional_code")  # DAT-019, DAT-020
    assert profiles_of_check(check) == (REGULATORY, EXPERT)


def test_every_check_has_a_profile() -> None:
    """Single edition (free software): the profile comes from the origin of every check."""
    assert all(profiles_of_check(c) for c in load_checks())


# ------------------------------------------------------------------ restriction
def test_restriction_keeps_only_the_codes_of_the_profile() -> None:
    found = [make_message("DAT-020", table="B_05.01", column="c0030", count=1, details="x")]
    results = evaluate_checks(found, ALL_RAN, "ZIP")
    regulatory = {r.definition.id: r for r in restrict_to_profile(results, REGULATORY)}
    expert = {r.definition.id: r for r in restrict_to_profile(results, EXPERT)}

    assert regulatory["data_additional_code"].definition.codes == ("DAT-019",)
    assert regulatory["data_additional_code"].status is CheckStatus.PASSED
    assert expert["data_additional_code"].status is CheckStatus.WARNING


def test_restriction_recomputes_the_weight_on_the_remaining_codes() -> None:
    results = evaluate_checks([], ALL_RAN, "XML")
    check = {r.definition.id: r for r in results}["env_single_declaration"]
    kept = {r.definition.id: r for r in restrict_to_profile(results, REGULATORY)}

    assert check.definition.weight == 5  # ENV-002, BLOCKER, PO_VALIDATED
    assert kept["env_single_declaration"].definition.codes == ("ENV-010",)
    assert kept["env_single_declaration"].definition.weight <= check.definition.weight


def test_restriction_keeps_a_blind_check_not_evaluated() -> None:
    results = evaluate_checks([], ALL_RAN, "ZIP", blind_codes={"DAT-019"})
    kept = {r.definition.id: r for r in restrict_to_profile(results, REGULATORY, {"DAT-019"})}
    assert kept["data_additional_code"].status is CheckStatus.NOT_EVALUATED


# ------------------------------------------------------------------ scores
def test_clean_file_scores_100_everywhere() -> None:
    computed = scores(evaluate_checks([], ALL_RAN, "ZIP"))

    assert computed.regulatory.value == computed.quality.value == 100
    assert computed.confidence.value == 100


def test_quality_score_is_the_formula_of_0_8_0_on_every_check() -> None:
    """No new formula (brief §9): the quality score is the 0.8.0 one, every check included."""
    found = [make_message("PKG-011", template="B_01.01")]
    results = evaluate_checks(found, ALL_RAN, "ZIP")
    reference = summarize(results)
    computed = scores(results).quality

    assert (computed.value, computed.earned, computed.total) == (
        reference.score,
        reference.earned,
        reference.total,
    )


def test_an_expert_finding_does_not_lower_the_regulatory_score() -> None:
    found = [make_message("DAT-020", table="B_05.01", column="c0030", count=1, details="x")]
    computed = scores(evaluate_checks(found, ALL_RAN, "ZIP"))

    assert computed.regulatory.value == 100
    assert computed.regulatory.earned == computed.regulatory.total
    # One minor warning out of ~240 points: rounded to 100, but the weight earned shows it.
    assert computed.quality.earned < computed.quality.total
    assert computed.quality.warnings == 1


def test_a_regulatory_blocker_lowers_both_scores_and_the_confidence() -> None:
    computed = scores(
        evaluate_checks([make_message("PKG-011", template="B_01.01")], ALL_RAN, "ZIP")
    )

    assert computed.regulatory.value is not None and computed.regulatory.value < 100
    assert computed.quality.value is not None and computed.quality.value < 100
    assert computed.confidence.value == 0


def test_provisional_rules_are_counted_and_reported() -> None:
    provisional = next(e["code"] for e in load_registry() if e["severity_status"] == "PROVISIONAL")
    computed = scores(evaluate_checks([], ALL_RAN, "ZIP"))

    assert computed.quality.provisional_codes >= 1
    assert computed.quality.provisional_findings == 0
    assert profile_of_code(provisional) in (REGULATORY, EXPERT)


def test_explanations_name_the_families_and_severities_taken_into_account() -> None:
    quality = scores(evaluate_checks([], ALL_RAN, "ZIP")).quality

    # DATA_QUALITY: the GLEIF consistency checks (branch feature/gleif-local).
    assert set(quality.origins) == {"OFFICIAL", "PO_VALIDATED", "TECHNICAL", "DATA_QUALITY"}
    assert {"BLOCKER", "MAJOR", "MINOR", "INFO"} <= set(quality.severities)
    assert "data" in quality.categories
    # Envelope checks do not concern a ZIP: out of the total, and said so.
    assert quality.not_applicable


def test_a_file_that_stops_early_is_not_evaluated_for_confidence() -> None:
    """PO-10 variant: 0 after a blocker, otherwise « not evaluated » if a check did not run."""
    steps = ALL_RAN | {"technical_rules": "SKIPPED"}
    result = confidence(evaluate_checks([], steps, "ZIP"))

    assert result.value is None
    assert result.not_run


def test_nothing_ran_is_never_a_zero() -> None:
    steps = dict.fromkeys(ALL_RAN, "SKIPPED")
    computed = scores(evaluate_checks([], steps, "UNKNOWN"))

    assert computed.confidence.value is None
    assert computed.regulatory.value is None and computed.quality.value is None
