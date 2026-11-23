# SPDX-License-Identifier: EUPL-1.2
"""Corrections de l'analyse red team du 07/11/2026 (docs/red-team-2026-11-07.md, CL-45)."""

import copy
import json
import time
from decimal import Decimal

import pytest

from contracts.messages import MAX_VALUE_LENGTH, Occurrence, clip, make_message
from import_engine.csv_importer import CsvImporter
from rules.business.amounts import _amount
from tests import factories
from tests.cases.golden import load_golden
from tests.cases.mutations import set_where
from tests.conftest import codes
from tests.test_business_amounts import PROVIDER_A
from tests.test_import_api import post
from tests.test_package_validator import parameters_with, validate, with_file

# A cut value: MAX_VALUE_LENGTH characters, then "… (+N)".
CUT = MAX_VALUE_LENGTH + 20


# ------------------------------------------------------------------ RT-17
def test_a_header_of_80_000_columns_is_read_in_linear_time(write) -> None:
    """``names.count`` for every name took 11 s for 40,000 columns and over 300 s for 300,000."""
    names = [f"c{index:05d}" for index in range(40_000)] * 2
    files = factories.default_files()
    files["reports/b_02.01.csv"] = (",".join(names) + "\n").encode()
    started = time.perf_counter()
    # The column limit of CL-46 (200) is lifted to measure the reading of the header itself.
    result = CsvImporter(max_columns=10**6).load(write("p.zip", factories.build_zip(files)))
    assert time.perf_counter() - started < 5
    assert codes(result.messages) == ["CSV-007"]
    assert len(result.messages[0].params["columns"]) <= CUT


# ------------------------------------------------------------------ RT-18
def test_a_long_value_is_cut_with_the_number_of_characters_left_out() -> None:
    assert clip("x" * MAX_VALUE_LENGTH) == "x" * MAX_VALUE_LENGTH
    assert clip("x" * (MAX_VALUE_LENGTH + 5)) == "x" * MAX_VALUE_LENGTH + "… (+5)"
    assert Occurrence(value="y" * 10**6).value == clip("y" * 10**6)
    assert Occurrence(value="court").value == "court"


def test_parameters_and_details_never_carry_a_whole_long_value() -> None:
    long = "z" * 10**6
    message = make_message("CSV-007", details=f"#1 · {long!r}\n#2 · 'ok'", file="f", columns=long)
    assert len(message.params["columns"]) <= CUT
    first, second = message.details.split("\n")
    assert len(first) <= CUT and second == "#2 · 'ok'"


def test_a_huge_cell_is_not_copied_whole_into_the_answer(client) -> None:
    package = copy.deepcopy(load_golden())
    # Under the cell limit of CL-46 (10,000 characters), above the copy limit (1,000).
    set_where(package, "B_05.01", "c0010", PROVIDER_A, "c0050", "N" * 9_000)
    response = post(client, package.name, package.to_zip())
    assert response.status_code == 200
    values = [
        place["value"]
        for message in response.json()["messages"]
        for place in message["occurrences"]
        if place["value"]
    ]
    assert any(value.startswith("NNN") for value in values)
    assert all(len(value) <= CUT for value in values)


# ------------------------------------------------------------- RT-19, RT-22
@pytest.mark.parametrize(
    "value", ["9E+999999", "9E+999999999", "1E-999999", "1" * 6_000, "0." + "1" * 100]
)
def test_an_absurd_amount_is_not_an_amount(value: str) -> None:
    assert _amount(value) is None


@pytest.mark.parametrize("value", ["0", "1000", "12345.67", "-3", "999999999999999999", "1E+6"])
def test_real_amounts_are_still_read(value: str) -> None:
    assert _amount(value) == Decimal(value)


@pytest.mark.parametrize("value", ["9E+999999", "9E+999999999"])
def test_an_absurd_amount_neither_stops_nor_feeds_the_rule(client, value: str) -> None:
    package = copy.deepcopy(load_golden())
    set_where(package, "B_05.01", "c0010", PROVIDER_A, "c0100", value)
    found = codes_of(post(client, package.name, package.to_zip()).json())
    assert "ENG-001" not in found and "DQ-014" not in found


def codes_of(body: dict) -> set[str]:
    return {message["code"] for message in body["messages"]}


# ------------------------------------------------------------------ RT-20
@pytest.mark.parametrize("name", ["decimalsInteger", "decimalsMonetary"])
def test_a_decimals_parameter_of_6_000_digits_is_a_finding(write, name: str) -> None:
    files = with_file("reports/parameters.csv", parameters_with(**{name: "-" + "9" * 6_000}))
    found = validate(write, files=files).messages
    assert codes(found).count("PKG-023") == 1
    assert len(found[codes(found).index("PKG-023")].params["value"]) <= CUT


@pytest.mark.parametrize("path", ["META-INF/reportPackage.json", "reports/report.json"])
@pytest.mark.parametrize(
    "content",
    [b"[" * 100_000 + b"]" * 100_000, json.dumps({"n": 0}).replace("0", "9" * 6_000).encode()],
    ids=["nested", "long-number"],
)
def test_a_json_file_nested_too_deeply_or_with_a_huge_number_is_invalid(
    write, path: str, content: bytes
) -> None:
    files = factories.default_files()
    files[path] = content
    assert "PKG-006" in codes(validate(write, files=files).messages)
