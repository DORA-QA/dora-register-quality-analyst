# SPDX-License-Identifier: EUPL-1.2
"""The performance measurement tool (CL-11) runs on a small synthetic package."""

from tools import measure_performance


def test_measure_on_a_small_synthetic_package() -> None:
    clean = measure_performance.measure(200)
    defective = measure_performance.measure(200, defect_every=10)

    assert clean.rows_loaded == 202
    # The synthetic package is not finding-free (DAT-005, DAT-014, DAT-017 on every provider, and
    # DQ-004: providers without arrangement); since PO-32 (#121) findings carry occurrences too.
    # Since 0.8.1, REL-007 covers every legal person: its providers, identified by a company
    # number, raise it as well.
    assert clean.findings == 5 and clean.occurrences > 0
    # Every tenth row is defective: an empty mandatory field, and since 0.7.8 the unknown
    # country eba_GA:ZZ outside the closed list L01 (DAT-033).
    assert defective.findings == clean.findings + 2
    # The response keeps a bounded weight: occurrences are capped per finding.
    assert defective.response_kb < 100


def test_render_is_a_markdown_table() -> None:
    table = measure_performance.render([measure_performance.measure(50)])

    assert table.startswith("| Scénario |")
    assert len(table.splitlines()) == 3


def test_joins_scenario_copies_the_golden_consistently() -> None:
    """Brief Sprint 3 §17.5: the copied golden keeps its own findings, nothing more."""
    run = measure_performance.measure(100, joins=True)

    assert run.scenario == "jointures (golden copié)"
    assert run.rows_requested >= 100
    # The copies raise the findings admitted for the golden (REL-007, DQ-006, REL-017) only.
    # DQ-014 (0.8.4): copied arrangements multiply the sums, not the totals of the providers.
    assert run.findings == 4


def test_measure_cli_accepts_the_joins_flag(capsys) -> None:
    measure_performance.main(["--joins", "20"])
    assert "jointures (golden copié)" in capsys.readouterr().out


def test_export_measure_reads_every_occurrence_and_exports_them() -> None:
    """CL-40: the export measure streams the whole report, nothing is written to disk."""
    result = measure_performance.measure_export(300)
    assert result.occurrences > 300
    assert result.pages_read > 25
    assert result.csv_mb > 0 and result.jsonl_mb > 0
    assert "| 300 |" in measure_performance.render_export([result])
