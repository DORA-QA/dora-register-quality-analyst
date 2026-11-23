# SPDX-License-Identifier: EUPL-1.2
"""Results kept by analysis (RT-13), client header (S6), every occurrence (Sprint 4, 0.8.3)."""

import copy
import time

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services.results_store import ResultsStore
from contracts import messages as messages_module
from contracts.messages import MAX_OCCURRENCES, Occurrence, make_message, with_occurrences
from tests import factories
from tests.cases.golden import load_golden
from tests.cases.mutations import MUTATIONS
from tests.test_import_api import ZIP_NAME, post


# ------------------------------------------------------------------ RT-13: results store
def test_store_keeps_the_last_two_results() -> None:
    store: ResultsStore[str] = ResultsStore(ttl_seconds=60)
    store.put("a", "A")
    store.put("b", "B")
    store.put("c", "C")

    assert store.get("a") is None
    assert (store.get("b"), store.get("c")) == ("B", "C")
    assert len(store) == 2


def test_reading_a_result_does_not_change_which_one_goes_first() -> None:
    """The oldest import goes first, even if it was read more recently."""
    store: ResultsStore[str] = ResultsStore(ttl_seconds=60)
    store.put("a", "A")
    store.put("b", "B")
    store.get("a")
    store.put("c", "C")
    assert store.get("a") is None


def test_results_expire_after_their_time(monkeypatch) -> None:
    store: ResultsStore[str] = ResultsStore(ttl_seconds=10)
    now = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: now)
    store.put("a", "A")
    monkeypatch.setattr(time, "monotonic", lambda: now + 11)
    assert store.get("a") is None


def test_delete_and_purge() -> None:
    store: ResultsStore[str] = ResultsStore(ttl_seconds=60)
    store.put("a", "A")
    store.put("b", "B")
    assert store.delete("a") and not store.delete("a")
    store.purge()
    assert len(store) == 0


def test_two_tabs_no_longer_erase_each_other(client) -> None:
    """RT-13: changing the language of the first analysis after a second import works."""
    first = post(client, ZIP_NAME, factories.build_zip()).json()["import_id"]
    post(client, ZIP_NAME, factories.build_zip())
    again = client.get(f"/api/import/{first}?lang=fr")
    assert again.status_code == 200
    assert again.json()["language"] == "fr"


def test_delete_forgets_an_analysis_and_its_register(client) -> None:
    first = post(client, ZIP_NAME, factories.build_zip()).json()["import_id"]

    assert client.delete(f"/api/import/{first}").status_code == 204
    assert client.get(f"/api/import/{first}").status_code == 404
    assert client.app.state.dataset_store.get(first) is None
    # Same answer when the analysis is already gone.
    assert client.delete(f"/api/import/{first}").status_code == 204


# ------------------------------------------------------------------ S6: client header
@pytest.fixture
def bare_client():
    with TestClient(app) as client:
        yield client


def test_import_without_the_client_header_is_refused(bare_client) -> None:
    answer = bare_client.post(
        "/api/import?lang=fr", files={"file": (ZIP_NAME, factories.build_zip())}
    )
    assert answer.status_code == 403
    assert "X-ROI-Client" in answer.json()["detail"]
    assert "refusée" in answer.json()["detail"]


def test_delete_without_the_client_header_is_refused(bare_client) -> None:
    assert bare_client.delete("/api/import/abc").status_code == 403


def test_an_empty_client_header_is_refused(bare_client) -> None:
    answer = bare_client.post(
        "/api/import",
        files={"file": (ZIP_NAME, factories.build_zip())},
        headers={"X-ROI-Client": " "},
    )
    assert answer.status_code == 403


def test_reading_needs_no_header(bare_client) -> None:
    """Reading changes nothing, and CORS already keeps another site from reading the answer."""
    assert bare_client.get("/api/languages").status_code == 200
    assert bare_client.get("/api/import/unknown").status_code == 404


def test_the_preflight_allows_the_header_only_for_the_known_origins(bare_client) -> None:
    def preflight(origin: str):
        return bare_client.options(
            "/api/import",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-roi-client",
            },
        )

    assert preflight("http://localhost:3000").status_code == 200
    assert preflight("https://evil.example").status_code == 400


# ------------------------------------------------------------------ every occurrence
def test_memory_keeps_every_occurrence_up_to_its_cap(monkeypatch) -> None:
    monkeypatch.setattr(messages_module, "MAX_STORED_OCCURRENCES", 30)
    places = [Occurrence("B_05.01", row=i, column="c0010", value="x") for i in range(1, 51)]
    kept = with_occurrences(make_message("FILE-001"), places)

    assert len(kept.occurrences) == 30
    assert kept.occurrences_total == 50


def many_rows_package() -> tuple[str, bytes]:
    """The golden with 60 providers whose LEI fails its check digits (DAT-008)."""
    from tests.cases.mutations import add_row

    golden = copy.deepcopy(load_golden())
    for i in range(60):
        add_row(golden, "B_01.02", c0010=f"5493001KJTIIGC8Y1R{i % 10}{(i + 3) % 10}")
    return golden.name, golden.to_zip()


@pytest.fixture
def big(client):
    name, content = many_rows_package()
    body = post(client, name, content).json()
    finding = max(body["messages"], key=lambda m: m["occurrences_total"])
    assert finding["occurrences_total"] > MAX_OCCURRENCES
    return client, body, finding


def test_the_answer_shows_25_and_says_how_many_are_available(big) -> None:
    _, _, finding = big
    assert len(finding["occurrences"]) == MAX_OCCURRENCES
    assert finding["occurrences_available"] == finding["occurrences_total"]
    assert isinstance(finding["index"], int)


def test_pages_cover_every_occurrence_in_order(big) -> None:
    client, body, finding = big
    url = f"/api/import/{body['import_id']}/findings/{finding['index']}/occurrences"
    seen = []
    offset = 0
    while True:
        page = client.get(url, params={"offset": offset, "limit": 20}).json()
        seen += page["occurrences"]
        offset += 20
        if offset >= page["matching"]:
            break

    assert len(seen) == finding["occurrences_total"]
    assert seen[:MAX_OCCURRENCES] == finding["occurrences"]
    assert page["code"] == finding["code"]


def test_filters_apply_to_every_occurrence_before_the_page(big) -> None:
    client, body, finding = big
    last = client.get(
        f"/api/import/{body['import_id']}/findings/{finding['index']}/occurrences",
        params={"offset": finding["occurrences_total"] - 1, "limit": 1},
    ).json()["occurrences"][0]
    assert last not in finding["occurrences"]  # beyond the first 25

    page = client.get(
        f"/api/import/{body['import_id']}/findings/{finding['index']}/occurrences",
        params={"row": last["row"], "table": last["table"]},
    ).json()
    assert page["matching"] >= 1
    assert all(o["row"] == last["row"] for o in page["occurrences"])

    matches = client.get(
        f"/api/import/{body['import_id']}/findings",
        params={"table": last["table"], "row": last["row"]},
    ).json()
    assert finding["index"] in [m["index"] for m in matches]


def test_unknown_finding_or_import_answers_404(big) -> None:
    client, body, _ = big
    assert (
        client.get(f"/api/import/{body['import_id']}/findings/999/occurrences").status_code == 404
    )
    assert client.get("/api/import/nope/findings/0/occurrences").status_code == 404


def test_page_size_is_bounded(big) -> None:
    client, body, finding = big
    url = f"/api/import/{body['import_id']}/findings/{finding['index']}/occurrences"
    assert client.get(url, params={"limit": 1001}).status_code == 422


# ------------------------------------------------------------------ #168: target in occurrences
@pytest.mark.parametrize(
    ("code", "target"),
    [
        ("REL-015", ("B_06.01", "c0050")),
        ("REL-016", ("B_06.01", "c0050")),
        ("REL-017", ("B_06.01", "c0050")),
        ("REL-020", None),
        ("REL-021", ("B_05.02", "c0030")),
    ],
)
def test_cross_table_occurrences_carry_their_target(client, code, target) -> None:
    mutation = next(m for m in MUTATIONS if m.code == code)
    name, content = mutation.apply(copy.deepcopy(load_golden()))
    finding = next(m for m in post(client, name, content).json()["messages"] if m["code"] == code)

    places = finding["occurrences"]
    assert places and all(p["target_table"] and p["target_column"] for p in places)
    if target:
        assert {(p["target_table"], p["target_column"]) for p in places} == {target}
