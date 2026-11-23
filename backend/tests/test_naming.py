# SPDX-License-Identifier: EUPL-1.2
from contracts.naming import (
    field_reference,
    file_name_from_table_code,
    table_code_from_file,
)


def test_table_code_and_file_name() -> None:
    assert table_code_from_file("b_01.01.csv") == "B_01.01"
    assert table_code_from_file("B_99.01.CSV") == "B_99.01"
    assert table_code_from_file("parameters.csv") is None
    assert file_name_from_table_code("B_05.02") == "b_05.02.csv"


def test_field_reference() -> None:
    assert field_reference("B_01.01") == "B_01.01"
    assert field_reference("B_06.01", "c0050") == "B_06.01.0050"
    assert field_reference("B_01.01", "_row") == "B_01.01"
    assert field_reference("other", "c0010") == "other"
