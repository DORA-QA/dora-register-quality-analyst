# SPDX-License-Identifier: EUPL-1.2
"""Plain-language overview of an analysis, built by rules, without AI (CL-37, #181).

Every sentence is assembled from figures the engine already computed (counts, scores, findings),
so that nothing is invented: a reader can check each number against the report. The texts are in
the language files (section ``overview``); this module only chooses them and fills them in.

Choices of the PO (04/11/2026, #181): verdict on fixed thresholds (a BLOCKER: cannot be filed;
a MAJOR: corrections expected; otherwise good quality), the three tables most concerned, the three
priorities (BLOCKER, MAJOR and MINOR findings, the most serious and widespread first).

Branch feature/gleif-local: one sentence on the verification of the LEI against the local GLEIF
copy (date of the copy, LEI checked, problems found by kind).
"""

from collections import Counter
from collections.abc import Sequence

from contracts.api_models import (
    MessageModel,
    OverviewModel,
    OverviewPriorityModel,
    ScoresModel,
    SeverityCounts,
)
from contracts.gleif import GleifCoverage
from contracts.messages import Joined, render_fragment, render_text, table_label

MAX_TABLES = 3
MAX_PRIORITIES = 3
RANK = {"BLOCKER": 0, "MAJOR": 1, "MINOR": 2, "INFO": 3}
# Kinds of GLEIF problems, in the order of the sentence (text key, field of GleifCoverage).
GLEIF_KINDS = (
    ("gleif_absent", "absent"),
    ("gleif_invalid", "invalid"),
    ("gleif_lapsed", "lapsed"),
    ("gleif_due", "due"),
    ("gleif_mismatch", "mismatches"),
)


def _text(key: str, language: str, **params: object) -> str:
    return render_text("overview", key, language, **params)


def _score(value: int | None, language: str) -> str:
    return _text("score_none", language) if value is None else f"{value}/100"


def _table_of(message: MessageModel) -> str | None:
    """Template a finding is about: the table of its first occurrence."""
    for occurrence in message.occurrences:
        if occurrence.table:
            return occurrence.table
    return None


def _gleif(coverage: GleifCoverage | None, language: str) -> str | None:
    if coverage is None:
        return None
    if not coverage.available:
        return _text("gleif_unavailable", language)
    if not coverage.checked:
        return None
    found = {key: int(getattr(coverage, field)) for key, field in GLEIF_KINDS}
    if not any(found.values()):
        return _text("gleif_ok", language, date=coverage.copy_date, checked=coverage.checked)
    parts = tuple(_text(key, language, count=count) for key, count in found.items() if count)
    return _text(
        "gleif_issues",
        language,
        date=coverage.copy_date,
        checked=coverage.checked,
        list=render_fragment(Joined(parts, "and"), language),
    )


def build_overview(
    messages: Sequence[MessageModel],
    counts: SeverityCounts,
    scores: ScoresModel | None,
    language: str,
    gleif: GleifCoverage | None = None,
) -> OverviewModel:
    if counts.blocker:
        verdict, headline = "BLOCKED", _text("verdict_blocked", language, count=counts.blocker)
    elif counts.major:
        verdict, headline = "CORRECTIONS", _text("verdict_corrections", language)
    elif counts.minor:
        verdict, headline = "GOOD", _text("verdict_good_minor", language, count=counts.minor)
    else:
        verdict, headline = "GOOD", _text("verdict_good", language)

    total = counts.blocker + counts.major + counts.minor + counts.info
    findings = (
        _text(
            "findings",
            language,
            total=total,
            blocker=counts.blocker,
            major=counts.major,
            minor=counts.minor,
            info=counts.info,
        )
        if total
        else _text("no_finding", language)
    )
    figures = _text(
        "figures",
        language,
        regulatory=_score(scores.regulatory.value if scores else None, language),
        quality=_score(scores.quality.value if scores else None, language),
        findings=findings,
    )

    by_table = Counter(t for t in (_table_of(m) for m in messages) if t)
    ranked = sorted(by_table.items(), key=lambda item: (-item[1], item[0]))[:MAX_TABLES]
    tables = (
        _text(
            "tables",
            language,
            list=render_fragment(
                Joined(
                    tuple(
                        _text(
                            "table_count",
                            language,
                            table=render_fragment(table_label(code), language),
                            count=count,
                        )
                        for code, count in ranked
                    ),
                    "and",
                ),
                language,
            ),
        )
        if ranked
        else None
    )

    serious = [m for m in messages if m.severity != "INFO"]
    serious.sort(key=lambda m: (RANK.get(m.severity, 9), -max(m.occurrences_total, 1)))
    priorities = [
        OverviewPriorityModel(
            index=m.index,
            code=m.code,
            severity=m.severity,
            finding=m.message,
            action=m.recommendation,
        )
        for m in serious[:MAX_PRIORITIES]
    ]

    official = sum(m.profile == "REGULATORY" for m in messages)
    expert = sum(m.profile == "EXPERT" for m in messages)
    profiles = (
        _text("profiles", language, official=official, expert=expert)
        if official or expert
        else None
    )
    return OverviewModel(
        verdict=verdict,
        headline=headline,
        figures=figures,
        tables=tables,
        gleif=_gleif(gleif, language),
        priorities=priorities,
        profiles=profiles,
        note=_text("note", language),
    )
