# SPDX-License-Identifier: EUPL-1.2
import polars as pl

from contracts import data_model
from import_engine.csv_importer import CsvImporter
from tests import factories
from tests.conftest import codes


def load(write, path: str | None = None, content: bytes | None = None):
    files = factories.default_files()
    if path:
        files[path] = content
    return CsvImporter().load(write("p.zip", factories.build_zip(files)))


def test_all_tables_are_loaded_as_text_with_row_numbers(write) -> None:
    result = load(write)

    assert result.messages == []
    assert result.total_tables == 15
    assert result.total_rows == 4  # B_01.01, B_01.02 and two providers
    providers = result.tables["B_05.01"]
    assert providers.columns == ["_row", *data_model.tables()["B_05.01"].columns]
    assert providers["_row"].to_list() == [1, 2]
    assert providers["c0050"].to_list() == ["Provider One", "Provider Two, Inc."]
    assert all(dtype == pl.String for dtype in providers.drop("_row").dtypes)


def test_values_are_never_converted(write) -> None:
    content = b"c0010,c0020\n007,2025-12-31\n1e5,true\n"

    table = load(write, "reports/b_02.01.csv", content).tables["B_02.01"]

    assert table["c0010"].to_list() == ["007", "1e5"]
    assert table["c0020"].to_list() == ["2025-12-31", "true"]


def test_header_only_file_is_an_empty_table(write) -> None:
    result = load(write)

    assert result.tables["B_99.01"].height == 0
    assert result.tables["B_99.01"].columns[:4] == ["_row", "c0010", "c0020", "c0030"]


def test_bom_is_accepted_with_a_minor_finding(write) -> None:
    result = load(write, "reports/b_02.01.csv", b"\xef\xbb\xbfc0010,c0020\nA,B\n")

    assert codes(result.messages) == ["CSV-002"]
    assert result.tables["B_02.01"].columns == ["_row", "c0010", "c0020"]


def test_unreadable_files_are_blocking_but_others_are_loaded(write) -> None:
    cases = {
        "CSV-001": "Entité,é\n".encode("latin-1"),
        "CSV-003": b"",
        "CSV-004": b"c0010,c0020\nA,B,C\n",
        "CSV-005": b"c0010;c0020\nA;B\n",
        "CSV-006": b"c0010,,c0020\nA,B,C\n",
        "CSV-007": b"c0010,c0010\nA,B\n",
    }
    for code, content in cases.items():
        result = load(write, "reports/b_02.01.csv", content)

        assert codes(result.messages) == [code], code
        assert "B_02.01" not in result.tables
        assert result.total_tables == 14


def test_empty_and_repeated_header_names_have_distinct_codes(write) -> None:
    """#109: an unnamed column is CSV-006, a repeated name is CSV-007 (both rule 801)."""
    trailing = load(write, "reports/b_02.01.csv", b"c0010,c0020,\nA,B,\n")
    repeated = load(write, "reports/b_02.01.csv", b"c0010,c0020,c0010,c0020\nA,B,C,D\n")

    crlf = load(write, "reports/b_02.01.csv", b"c0010,c0020,\r\nA,B,\r\n")

    assert codes(trailing.messages) == ["CSV-006"]
    assert codes(crlf.messages) == ["CSV-006"]
    assert codes(repeated.messages) == ["CSV-007"]
    assert repeated.messages[0].params["columns"] == "c0010, c0020"


def test_stray_carriage_return_in_the_header_is_a_finding_not_a_crash(write) -> None:
    """A lone CR inside the header row used to raise csv.Error (HTTP 500).

    Since 09/11/2026 the lone CR is also reported for itself (CSV-012).
    """
    result = load(write, "reports/b_02.01.csv", b"c0010\r,c0020\nA,B\n")

    assert codes(result.messages) == ["CSV-012", "CSV-004"]
    assert "B_02.01" not in result.tables


def test_lf_and_crlf_line_endings_are_accepted(write) -> None:
    """ECB check of 02/10/2026: LF and CR+LF are the two accepted line endings."""
    for content in (b"c0010,c0020\nA,B\n", b"c0010,c0020\r\nA,B\r\n"):
        result = load(write, "reports/b_02.01.csv", content)

        assert result.messages == []


def test_last_line_without_line_break_is_major_and_the_table_is_loaded(write) -> None:
    result = load(write, "reports/b_02.01.csv", b"c0010,c0020\r\nA,B\r\nC,D")

    assert codes(result.messages) == ["CSV-011"]
    assert result.messages[0].severity == "MAJOR"
    assert result.messages[0].params["line"] == 3
    assert result.tables["B_02.01"]["c0010"].to_list() == ["A", "C"]


def test_header_only_file_without_line_break_is_reported(write) -> None:
    result = load(write, "reports/b_02.01.csv", b"c0010,c0020")

    assert codes(result.messages) == ["CSV-011"]
    assert result.messages[0].params["line"] == 1


def test_lone_carriage_returns_are_counted_with_the_first_line(write) -> None:
    content = b"c0010,c0020\nA,B\rC,D\rE,F\n"

    result = load(write, "reports/b_02.01.csv", content)

    assert "CSV-012" in codes(result.messages)
    found = next(m for m in result.messages if m.code == "CSV-012")
    assert found.severity == "MAJOR"
    assert found.params["line"] == 2
    assert found.params["count"] == 2
    assert "CSV-011" not in codes(result.messages)


def test_last_line_ending_with_a_lone_carriage_return_is_csv_012_only(write) -> None:
    result = load(write, "reports/b_02.01.csv", b"c0010,c0020\nA,B\r")

    assert codes(result.messages) == ["CSV-012"]
    assert result.messages[0].params["line"] == 2


def test_line_breaks_inside_quoted_cells_are_cell_content(write) -> None:
    content = b'c0010,c0020\r\n"one\rtwo","three\r\nfour"\r\n'

    result = load(write, "reports/b_02.01.csv", content)

    assert result.messages == []
    assert result.tables["B_02.01"]["c0010"].to_list() == ["one\rtwo"]


def test_a_file_of_lone_carriage_returns_is_read_in_linear_time(write) -> None:
    """Red team habit: an old Mac file of 200 000 lines must not be quadratic."""
    import time

    content = b"c0010,c0020" + b"\rA,B" * 200_000 + b"\r"
    started = time.perf_counter()
    result = load(write, "reports/b_02.01.csv", content)

    assert time.perf_counter() - started < 5
    found = next(m for m in result.messages if m.code == "CSV-012")
    assert found.params["count"] == 200_001
    assert found.params["line"] == 1
