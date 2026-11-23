# SPDX-License-Identifier: EUPL-1.2
"""The test case register follows the catalog (severities and their status)."""

import csv

from tests.cases.build_register import REGISTER, build_rows


def test_register_matches_catalog() -> None:
    with REGISTER.open(encoding="utf-8", newline="") as handle:
        current = [
            (row["cas"], row["severite"], row["statut_severite"]) for row in csv.DictReader(handle)
        ]
    expected = [(row["cas"], row["severite"], row["statut_severite"]) for row in build_rows()]
    assert current == expected, "Régénérer : python -m tests.cases.build_register"
