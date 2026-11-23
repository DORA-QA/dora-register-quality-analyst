# SPDX-License-Identifier: EUPL-1.2
"""Plain-language overview built by rules (CL-37, #181)."""

from contracts.api_models import MessageModel, OccurrenceModel, SeverityCounts
from reports.overview import build_overview


def message(
    code: str, severity: str, table: str | None, total: int = 1, profile: str = "REGULATORY"
):
    return MessageModel(
        code=code,
        severity=severity,
        message=f"finding {code}",
        recommendation=f"fix {code}",
        occurrences=[OccurrenceModel(table=table, row=1)] if table else [],
        occurrences_total=total,
        profile=profile,
        index=0,
    )


def counts(blocker: int = 0, major: int = 0, minor: int = 0, info: int = 0) -> SeverityCounts:
    return SeverityCounts(blocker=blocker, major=major, minor=minor, info=info)


def test_verdict_follows_the_most_serious_finding() -> None:
    assert build_overview([], counts(blocker=2), None, "fr").verdict == "BLOCKED"
    assert build_overview([], counts(major=1, minor=4), None, "fr").verdict == "CORRECTIONS"
    good = build_overview([], counts(minor=2), None, "fr")
    assert good.verdict == "GOOD" and "2 point(s) mineur(s)" in good.headline
    assert build_overview([], counts(), None, "en").headline == "The register is of good quality."


def test_figures_never_show_a_missing_score_as_zero() -> None:
    overview = build_overview([], counts(), None, "fr")
    assert "non évalué" in overview.figures and "Aucun constat." in overview.figures


def test_tables_are_named_with_their_official_title_and_ranked() -> None:
    found = [
        message("DAT-024", "MAJOR", "B_07.01"),
        message("DAT-033", "MAJOR", "B_07.01"),
        message("REL-009", "MAJOR", "B_02.01", profile="EXPERT"),
        message("PKG-010", "INFO", None),
    ]
    overview = build_overview(found, counts(major=3, info=1), None, "fr")
    assert overview.tables == (
        "Les constats se concentrent sur « Évaluation des services TIC » (B_07.01) "
        "(2 constat(s)) et « Accords contractuels — Informations générales » (B_02.01) "
        "(1 constat(s))."
    )
    assert overview.profiles is not None and overview.profiles.startswith("3 constat(s)")


def test_priorities_are_the_three_most_serious_and_widespread_never_info() -> None:
    found = [
        message("INFO-1", "INFO", "B_01.01", total=500),
        message("MINOR-1", "MINOR", "B_01.01", total=200),
        message("MAJOR-SMALL", "MAJOR", "B_01.01", total=1),
        message("MAJOR-WIDE", "MAJOR", "B_01.01", total=40),
        message("BLOCK", "BLOCKER", "B_01.01", total=2),
    ]
    overview = build_overview(found, counts(blocker=1, major=2, minor=1, info=1), None, "en")
    assert [p.code for p in overview.priorities] == ["BLOCK", "MAJOR-WIDE", "MAJOR-SMALL"]
    assert overview.priorities[0].action == "fix BLOCK"


def test_gleif_sentence_counts_the_problems_by_kind() -> None:
    """Branch feature/gleif-local: the summary says how the LEI fared against GLEIF."""
    from contracts.gleif import GleifCoverage

    coverage = GleifCoverage(
        available=True, checked=12, copy_date="2026-11-08", absent=7, lapsed=1, mismatches=3
    )
    text = build_overview([], counts(major=2, minor=3), None, "fr", gleif=coverage).gleif
    assert text == (
        "Vérification GLEIF (copie du 2026-11-08) : 12 LEI vérifiés ; 7 introuvable(s), "
        "1 non renouvelé(s) et 3 écart(s) de pays, de nom ou de mère avec le GLEIF."
    )
    clean = GleifCoverage(available=True, checked=12, copy_date="2026-11-08")
    assert build_overview([], counts(), None, "en", gleif=clean).gleif == (
        "GLEIF check (copy of 2026-11-08): the 12 LEI checked are found, valid and consistent "
        "with the register."
    )
    missing = GleifCoverage(available=False, checked=12, copy_date=None)
    assert "aucune copie" in build_overview([], counts(), None, "fr", gleif=missing).gleif
    assert build_overview([], counts(), None, "fr").gleif is None  # GLEIF switched off
    nothing = GleifCoverage(available=True, checked=0, copy_date="2026-11-08")
    assert build_overview([], counts(), None, "fr", gleif=nothing).gleif is None
