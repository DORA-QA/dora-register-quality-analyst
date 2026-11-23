# SPDX-License-Identifier: EUPL-1.2
"""Chaque erreur introduite dans le package golden est détectée ; le golden est propre."""

import copy

import pytest

from tests.cases.golden import load_golden
from tests.cases.mutations import MUTATIONS
from tests.test_import_api import post
from tests.test_sample_data_golden import admitted_findings

# The mutations add short rows (a key and one value): the EBA conditional rules (DAT-023 to
# DAT-026) rightly complain about the missing companion values. These side effects are expected
# everywhere and are not listed one by one in ``also``.
CONDITIONAL_SIDE_EFFECTS = {"DAT-023", "DAT-024", "DAT-025", "DAT-026"}
# Findings the golden raises by decision of the PO (sample-data/golden-manifest.sample.json):
# present in every mutation, they are not listed one by one either.
GOLDEN_ADMITTED = set(admitted_findings())
# Mutations adding a short provider row to B_05.01 leave it unused: DQ-004 (INFO) follows.
UNUSED_PROVIDER = {"DQ-004"}


def test_golden_package_is_clean(client) -> None:
    golden = load_golden()
    body = post(client, golden.name, golden.to_zip()).json()

    assert {m["code"] for m in body["messages"]} == GOLDEN_ADMITTED


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda m: m.case)
def test_mutation_is_detected(client, mutation) -> None:
    name, content = mutation.apply(copy.deepcopy(load_golden()))
    found = {m["code"] for m in post(client, name, content).json()["messages"]}

    assert mutation.code in found, f"{mutation.description}: {sorted(found)}"
    others = found - {mutation.code} - CONDITIONAL_SIDE_EFFECTS - GOLDEN_ADMITTED - UNUSED_PROVIDER
    assert others <= set(mutation.also), sorted(found)


# Findings on the whole table, without a place in the data: DAT-002 (no row at all).
TABLE_LEVEL = {"DAT-002"}
# Findings on header columns: located on a column, without a row.
COLUMN_LEVEL = {"DAT-001", "DAT-030"}
DATA_PREFIXES = ("DAT-", "REL-", "BUS-", "DQ-")
DATA_MUTATIONS = [
    m for m in MUTATIONS if m.code.startswith(DATA_PREFIXES) and m.code not in TABLE_LEVEL
]


@pytest.mark.parametrize("mutation", DATA_MUTATIONS, ids=lambda m: m.case)
def test_data_findings_are_located_on_table_row_column(client, mutation) -> None:
    """Brief, epic 9 and §15: every data finding is located (table, row, column, value)."""
    name, content = mutation.apply(copy.deepcopy(load_golden()))
    body = post(client, name, content).json()
    finding = next(m for m in body["messages"] if m["code"] == mutation.code)
    places = finding["occurrences"]

    assert places, f"{mutation.code}: no structured occurrence"
    assert all(p["table"] and p["column"] for p in places), places
    if mutation.code not in COLUMN_LEVEL:
        assert all(isinstance(p["row"], int) and p["row"] >= 1 for p in places), places
    assert finding["occurrences_total"] >= len(places)
