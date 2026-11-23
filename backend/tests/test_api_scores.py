# SPDX-License-Identifier: EUPL-1.2
"""Scores, profiles and versions in the API answer (Sprint 4, 0.8.2): additions only."""

import re

from api.config import APP_VERSION
from contracts.messages import load_catalog
from tests import factories
from tests.cases.golden import load_golden
from tests.test_import_api import ZIP_NAME, post

# Fields of the 0.8.0 answer that clients may read: they stay, with the same meaning.
SUMMARY_0_8_0 = {
    "checks_performed",
    "passed",
    "warnings",
    "failed",
    "rows_analysed",
    "score",
    "weight_earned",
    "weight_total",
    "quality_score",
    "confidence_score",
}


def test_the_0_8_0_summary_is_unchanged(client) -> None:
    body = post(client, ZIP_NAME, factories.build_zip()).json()

    assert set(body["summary"]) >= SUMMARY_0_8_0
    assert "edition" not in body["summary"]


def test_scores_by_profile_with_their_computation(client) -> None:
    body = post(client, ZIP_NAME, factories.build_zip()).json()
    scores = body["scores"]

    assert scores["regulatory"]["scope"] == "REGULATORY"
    assert scores["quality"]["scope"] == "QUALITY"
    assert scores["regulatory"]["state"] == scores["quality"]["state"] == "EVALUATED"
    assert scores["confidence"] == {"value": 100, "state": "EVALUATED", "not_run": []}
    assert set(scores["regulatory"]["origins"]) <= {"OFFICIAL", "TECHNICAL"}
    assert scores["engine_version"] == APP_VERSION
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00", scores["computed_at"])


def test_engine_versions(client) -> None:
    engine = post(client, ZIP_NAME, factories.build_zip()).json()["engine"]

    assert engine["version"] == APP_VERSION
    assert engine["catalog_codes"] == len(load_catalog())
    assert re.fullmatch(r"[0-9a-f]{12}", engine["catalog_fingerprint"])
    assert engine["taxonomy_version"] == "4.0"


def test_every_finding_and_check_carries_its_profile(client) -> None:
    golden = load_golden()
    body = post(client, golden.name, golden.to_zip()).json()

    assert body["messages"]
    assert all(m["profile"] in ("REGULATORY", "EXPERT") for m in body["messages"])
    assert all(c["profiles"] for c in body["checks"])
    by_origin = {(m["origin"], m["profile"]) for m in body["messages"]}
    assert ("PO_VALIDATED", "REGULATORY") not in by_origin
    assert ("OFFICIAL", "EXPERT") not in by_origin


def test_concentration_state(client) -> None:
    golden = load_golden()
    body = post(client, golden.name, golden.to_zip()).json()
    assert body["concentration_state"] == "EVALUATED"
    # CL-43: values carry their label (official ITS label, else the EBA one).
    services = body["concentration"]["by_service_type"]["items"]
    assert all(item["label"] for item in services if item["key"])

    minimal = post(client, ZIP_NAME, factories.build_zip()).json()
    assert minimal["concentration"] is None
    assert minimal["concentration_state"] == "NOT_APPLICABLE"


def test_a_file_that_is_not_a_register_scores_low_with_no_confidence(client) -> None:
    """Detection ran and failed: a score exists, it is low, and the confidence is 0."""
    body = post(client, "note.txt", b"not a register").json()

    assert body["scores"]["regulatory"]["state"] == "EVALUATED"
    assert body["scores"]["regulatory"]["value"] < 10
    assert body["scores"]["confidence"]["value"] == 0
