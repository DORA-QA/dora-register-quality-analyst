# SPDX-License-Identifier: EUPL-1.2
"""Tout code du catalogue est couvert par une mutation, ou listé comme à fabriquer."""

import csv

from contracts.messages import load_catalog
from tests.cases.build_register import REGISTER, build_rows
from tests.cases.mutations import MANUAL, MUTATIONS


def test_every_catalog_code_is_covered_or_declared_manual() -> None:
    mutated = {mutation.code for mutation in MUTATIONS}
    uncovered = [code for code in load_catalog() if code not in mutated and code not in MANUAL]
    assert uncovered == []


def test_no_code_is_both_mutated_and_manual() -> None:
    assert {mutation.code for mutation in MUTATIONS} & set(MANUAL) == set()


def test_every_register_row_has_the_header_columns() -> None:
    """A comment with an unquoted comma once split a row into extra columns (27/10)."""
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        width = len(next(reader))
        wrong = [row[0] for row in reader if len(row) != width]
    assert wrong == []


def test_register_file_is_up_to_date() -> None:
    with REGISTER.open(encoding="utf-8", newline="") as handle:
        stored = [row["cas"] for row in csv.DictReader(handle)]
    assert stored == [row["cas"] for row in build_rows()]
