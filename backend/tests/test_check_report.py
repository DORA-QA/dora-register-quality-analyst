# SPDX-License-Identifier: EUPL-1.2
"""The registry covers every finding and the score behaves as announced."""

from contracts.check_report import CheckStatus, evaluate_checks, load_checks
from contracts.messages import load_catalog, load_texts, make_message, supported_languages
from scoring import summarize


def blocker(code: str):
    return make_message(code)


ALL_RAN = {
    key: "OK"
    for key in (
        "detection",
        "xml_validation",
        "extraction",
        "zip_validation",
        "package_validation",
        "csv_import",
        "dataset",
        "technical_rules",
    )
}


def test_every_code_belongs_to_exactly_one_check() -> None:
    codes = [code for check in load_checks() for code in check.codes]
    assert sorted(codes) == sorted(load_catalog())


def test_every_check_and_category_has_a_label_in_every_language() -> None:
    for language in supported_languages():
        texts = load_texts(language)
        for check in load_checks():
            assert texts["checks"][check.id], (language, check.id)
            assert texts["categories"][check.category], (language, check.category)


def test_clean_file_scores_100() -> None:
    results = evaluate_checks([], ALL_RAN, "ZIP")
    summary = summarize(results)

    assert summary.score == 100
    assert summary.failed == summary.warnings == 0


def test_blocker_fails_a_check_and_lowers_the_score() -> None:
    results = evaluate_checks([make_message("PKG-011", template="B_01.01")], ALL_RAN, "ZIP")
    summary = summarize(results)

    assert summary.failed == 1
    assert summary.score is not None and summary.score < 100


def test_lighter_findings_only_warn() -> None:
    results = evaluate_checks([make_message("PKG-025", count="1", files="a\\b")], ALL_RAN, "ZIP")
    statuses = {r.definition.id: r.status for r in results}

    assert statuses["pkg_files"] is CheckStatus.WARNING
    assert summarize(results).failed == 0


def test_steps_that_did_not_run_are_skipped() -> None:
    steps = dict.fromkeys(ALL_RAN, "SKIPPED") | {"detection": "FAILED"}
    results = evaluate_checks([make_message("FILE-001")], steps, "UNKNOWN")
    summary = summarize(results)

    assert summary.performed == 2
    assert summary.failed == 1


def test_a_file_that_stops_early_cannot_score_high() -> None:
    steps = dict.fromkeys(ALL_RAN, "SKIPPED") | {"detection": "OK", "xml_validation": "FAILED"}
    results = evaluate_checks([make_message("XML-002", details="x")], steps, "XML")
    summary = summarize(results)

    assert summary.performed < summary.total
    assert summary.score is not None and summary.score < 40


def test_inapplicable_checks_do_not_lower_the_score() -> None:
    results = evaluate_checks([], ALL_RAN, "ZIP")

    assert summarize(results).score == 100


def test_the_registry_has_no_commercial_edition() -> None:
    from contracts.check_report import load_registry

    assert all("edition" not in entry for entry in load_registry())


def test_registry_has_one_entry_per_code_aligned_with_catalog_and_texts() -> None:
    from contracts.check_report import load_registry

    registry = load_registry()
    codes = [entry["code"] for entry in registry]
    catalog = load_catalog()

    assert len(codes) == len(set(codes))
    assert set(codes) == set(catalog)
    for language in supported_languages():
        assert set(load_texts(language)["messages"]) == set(codes), language
    for entry in registry:
        definition = catalog[entry["code"]]
        assert entry["source"] == definition["reference"]["type"], entry["code"]
        assert entry["severity_status"] == definition.get("severity_status", "CONFIRMED")
        assert entry["introduced"].count(".") == 2, entry["code"]
        assert entry["group"], entry["code"]


def test_entries_of_a_group_share_category_step_and_scope() -> None:
    from contracts.check_report import load_registry

    by_group: dict[str, set[tuple]] = {}
    for entry in load_registry():
        by_group.setdefault(entry["group"], set()).add(
            (entry["category"], entry["step"], entry["xml_only"])
        )
    assert all(len(values) == 1 for values in by_group.values())


def test_confidence_is_100_without_blocker_and_0_with_one() -> None:
    from scoring import summarize

    results = evaluate_checks([], ALL_RAN, "ZIP")
    assert summarize(results).confidence == 100
    blocked = evaluate_checks([blocker("PKG-021")], ALL_RAN, "ZIP")
    assert summarize(blocked).confidence == 0
    assert summarize(blocked).score is not None


def test_every_check_counts_in_the_scores() -> None:
    from contracts.check_report import CheckDefinition, CheckResult, CheckStatus
    from scoring import summarize

    base = evaluate_checks([], ALL_RAN, "ZIP")
    extra = CheckDefinition(
        id="EXTRA-X", category="x", step="x", codes=("EXP-1",), xml_only=False, weight=5
    )
    results = [*base, CheckResult(extra, CheckStatus.FAILED, ("EXP-1",))]
    assert summarize(results).confidence == 0
    assert summarize(results).score < summarize(base).score


def test_every_code_has_a_known_origin_and_validation_status() -> None:
    """CL-30: origin is an attribute; product codes never claim an authority (RT-06)."""
    from contracts.check_report import ORIGINS, SEVERITY_STATUSES, load_registry

    for entry in load_registry():
        code = entry["code"]
        assert entry["origin"] in ORIGINS, code
        assert entry["severity_status"] in SEVERITY_STATUSES, code
        if entry["source"] in ("regulatory", "official_guide"):
            assert entry["origin"] == "OFFICIAL", code
        else:
            assert entry["origin"] != "OFFICIAL", code
        # A decision of the Product Owner is never presented as confirmed by an authority.
        if entry["origin"] == "PO_VALIDATED":
            # PROVISIONAL when the PO raised the severity without a rejection source (REL-012).
            assert entry["severity_status"] in ("PO_VALIDATED", "PROVISIONAL"), code


def test_the_product_decisions_of_the_po_are_po_validated() -> None:
    """Decision P5 of the Sprint 3 (28/10/2026), DAT-020 (RT-08, PO decision of 31/10/2026) and
    DAT-035 (natural person with a LEI, PO decision of 02/11/2026)."""
    from contracts.check_report import load_registry

    sprint3 = ("REL-", "BUS-", "DQ-")
    decided = {
        e["code"]
        for e in load_registry()
        if e["origin"] == "PO_VALIDATED" and not e["code"].startswith(sprint3)
    }
    assert decided == {"ENV-002", "ENV-009", "PKG-024", "PKG-025", "DAT-020", "DAT-035"}


def test_origin_and_tables_reach_the_checks_and_the_findings() -> None:
    from contracts.check_report import load_checks, origin_of_code

    assert origin_of_code("DAT-005") == "OFFICIAL"
    assert origin_of_code("ZIP-001") == "TECHNICAL"
    assert origin_of_code("UNKNOWN") is None
    assert all(check.origins for check in load_checks())
