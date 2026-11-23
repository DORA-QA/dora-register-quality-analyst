# SPDX-License-Identifier: EUPL-1.2
"""The severity of a finding follows the EBA rejection rule (provisional mapping)."""

import json
from pathlib import Path

from contracts.messages import load_catalog

MAPPING_FILE = (
    Path(__file__).resolve().parent.parent / "reference" / "checks" / "severity-mapping.json"
)
MAPPING = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))


def test_mapping_is_provisional_and_sourced() -> None:
    assert MAPPING["status"] == "PROVISIONAL"
    assert MAPPING["source"].strip()
    assert MAPPING["mapping"] == {"rejects": "BLOCKER", "does_not_reject": "MAJOR"}


def test_catalog_severity_follows_the_rejection_rule() -> None:
    mapped = MAPPING["mapping"]
    for code, entry in load_catalog().items():
        rules = [MAPPING["rules"][o] for o in entry["official_codes"] if o in MAPPING["rules"]]
        if not rules or code in MAPPING["exceptions"]:
            continue
        expected = (
            mapped["rejects"] if any(r["rejects"] for r in rules) else mapped["does_not_reject"]
        )
        assert entry["severity"] == expected, code


def test_exceptions_exist_in_the_catalog() -> None:
    assert set(MAPPING["exceptions"]) <= set(load_catalog())
