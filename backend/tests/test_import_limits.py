# SPDX-License-Identifier: EUPL-1.2
"""Plafonds de l'import (CL-46, décisions du PO du 07/11/2026 ; red team RT-21)."""

import copy

from api.config import Settings
from import_engine.csv_importer import MAX_CELL_CHARACTERS, MAX_COLUMNS, MAX_ROWS, CsvImporter
from tests import factories
from tests.cases.golden import load_golden
from tests.conftest import codes
from tests.test_import_api import post


def load(write, importer: CsvImporter, **files: bytes):
    content = factories.default_files()
    content.update({f"reports/{name}.csv": data for name, data in files.items()})
    return importer.load(write("p.zip", factories.build_zip(content)))


def test_the_limits_decided_by_the_po() -> None:
    assert (MAX_CELL_CHARACTERS, MAX_COLUMNS, MAX_ROWS) == (10_000, 200, 2_000_000)
    settings = Settings()
    assert (settings.max_cell_characters, settings.max_columns, settings.max_rows) == (
        10_000,
        200,
        2_000_000,
    )


def test_a_cell_at_the_limit_is_loaded_and_one_more_character_is_refused(write) -> None:
    importer = CsvImporter(max_cell_characters=20)
    kept = load(write, importer, **{"b_01.01": b"c0010,c0020\n" + "é".encode() * 20 + b",B\n"})
    assert "B_01.01" in kept.tables and codes(kept.messages) == []

    # Counted in characters, not in bytes.
    refused = load(write, importer, **{"b_01.01": b"c0010,c0020\nA,B\nC," + "é".encode() * 21})
    assert "B_01.01" not in refused.tables
    (message,) = refused.messages
    assert message.code == "CSV-008"
    assert (message.params["file"], message.params["line"], message.params["limit"]) == (
        "reports/b_01.01.csv",
        3,
        20,
    )


def test_a_long_quoted_cell_spread_over_several_lines_is_measured_whole(write) -> None:
    cell = b'"' + b"ligne\n" * 10 + b'"'
    refused = load(write, CsvImporter(max_cell_characters=50), **{"b_01.01": b"c0010\n" + cell})
    assert codes(refused.messages) == ["CSV-008"]


def test_the_limit_of_the_csv_module_is_restored(write) -> None:
    import csv

    before = csv.field_size_limit()
    load(write, CsvImporter(max_cell_characters=20), **{"b_01.01": b"c0010\n" + b"x" * 30})
    assert csv.field_size_limit() == before


def test_too_many_columns_are_refused_before_the_table_is_read(write) -> None:
    widest = max(
        len(f.split(b"\n", 1)[0].split(b","))
        for p, f in factories.default_files().items()
        if "b_" in p
    )
    importer = CsvImporter(max_columns=widest)
    assert codes(load(write, importer).messages) == []
    header = ",".join(f"c{index:04d}" for index in range(widest + 1)).encode()
    refused = load(write, importer, **{"b_01.01": header + b"\n"})
    assert codes(refused.messages) == ["CSV-009"] and "B_01.01" not in refused.tables
    params = refused.messages[0].params
    assert (params["file"], params["count"], params["limit"]) == (
        "reports/b_01.01.csv",
        widest + 1,
        widest,
    )


def test_past_the_row_limit_nothing_is_loaded(write) -> None:
    rows = sum(len(f.splitlines()) - 1 for p, f in factories.default_files().items() if "b_" in p)
    assert codes(load(write, CsvImporter(max_rows=rows)).messages) == []

    refused = load(write, CsvImporter(max_rows=rows - 1))
    assert codes(refused.messages) == ["CSV-010"]
    assert refused.tables == {} and refused.summaries == []


def test_a_register_past_the_row_limit_is_not_analysed(client) -> None:
    package = copy.deepcopy(load_golden())
    package.files["reports/b_99.01.csv"] += b"x\n" * MAX_ROWS
    body = post(client, package.name, package.to_zip()).json()
    assert body["status"] == "FAILED"
    found = {message["code"] for message in body["messages"]}
    assert {"CSV-010", "IMP-001"} <= found
    # No table, so no rule: a partial register would give misleading findings.
    assert not any(code.startswith(("DAT-", "REL-", "DQ-", "BUS-")) for code in found)
