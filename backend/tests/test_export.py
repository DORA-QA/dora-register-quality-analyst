# SPDX-License-Identifier: EUPL-1.2
"""Export of the findings as CSV and JSON Lines (Sprint 4, lot 3, §15 and §16)."""

import csv
import io
import json

from contracts.disclaimer import DISCLAIMER
from reports.export import FIELDS, csv_stream, jsonl_stream, neutralise
from tests.test_import_api import post
from tests.test_results_and_occurrences import big, many_rows_package  # noqa: F401


def read_csv(body: bytes) -> list[dict[str, str]]:
    """The finding lines, without the disclaimer that closes the file."""
    text = body.decode("utf-8")
    assert text.startswith("﻿")
    content, _, closing = text[1:].partition("\r\n\r\n")
    assert next(csv.reader(io.StringIO(closing), delimiter=";"))[0] in DISCLAIMER.values()
    return list(csv.DictReader(io.StringIO(content + "\r\n"), delimiter=";"))


def test_there_are_22_fields_with_english_headers() -> None:
    assert len(FIELDS) == 22
    header = "".join(csv_stream([])).lstrip("﻿").splitlines()[0]
    assert header.split(";") == list(FIELDS)


def test_formulas_are_neutralised() -> None:
    for text in ("=SUM(A1)", "+33", "-1", "@cmd", "\tx", "\rx"):
        assert neutralise(text) == f"'{text}"
    assert neutralise("ACME") == "ACME"
    assert neutralise(None) == ""
    assert neutralise(3) == "3"


def test_csv_has_one_line_per_occurrence_beyond_the_25_of_the_answer(big) -> None:  # noqa: F811
    client, body, finding = big
    answer = client.get(f"/api/import/{body['import_id']}/export.csv?lang=fr")
    assert answer.status_code == 200
    assert answer.headers["content-type"].startswith("text/csv")
    assert answer.headers["cache-control"] == "no-store"
    disposition = answer.headers["content-disposition"]
    assert f"dora-qa-findings-{body['import_id']}-" in disposition and disposition.endswith('.csv"')
    lines = read_csv(answer.content)
    expected = sum(max(m["occurrences_total"], 1) for m in body["messages"])
    assert len(lines) == expected
    mine = [line for line in lines if line["finding_index"] == str(finding["index"])]
    assert len(mine) == finding["occurrences_total"]
    assert {line["engine_version"] for line in lines} == {body["engine"]["version"]}
    assert all(line["message"] for line in lines)
    assert {line["profile"] for line in lines} <= {"REGULATORY", "EXPERT"}


def test_the_file_name_never_carries_the_name_of_the_file_analysed(client) -> None:
    name, content = many_rows_package()
    body = post(client, name, content).json()
    answer = client.get(f"/api/import/{body['import_id']}/export.jsonl")
    assert name.removesuffix(".zip") not in answer.headers["content-disposition"]


def test_values_can_be_excluded(big) -> None:  # noqa: F811
    client, body, finding = big
    url = f"/api/import/{body['import_id']}/export.csv"
    with_values = read_csv(client.get(url).content)
    without = read_csv(client.get(url, params={"values": "false"}).content)
    assert any(line["source_value"] for line in with_values)
    assert not any(line["source_value"] for line in without)
    assert len(with_values) == len(without)


def test_the_filters_of_the_screen_apply(big) -> None:  # noqa: F811
    client, body, finding = big
    url = f"/api/import/{body['import_id']}/export.jsonl"
    row = finding["occurrences"][0]["row"]
    only = client.get(url, params={"findings": str(finding["index"]), "row": row})
    lines = [json.loads(line) for line in only.text.splitlines()]
    assert lines.pop() == {"record_type": "disclaimer", "text": DISCLAIMER["en"]}
    assert lines and all(line["finding_index"] == finding["index"] for line in lines)
    assert all(line["source_row"] == row for line in lines)
    assert set(lines[0]) == set(FIELDS)


def test_unknown_import_or_bad_filter(client, big) -> None:  # noqa: F811
    _, body, _ = big
    assert client.get("/api/import/nope/export.csv").status_code == 404
    bad = client.get(f"/api/import/{body['import_id']}/export.csv", params={"findings": "a"})
    assert bad.status_code == 400
    assert client.get(f"/api/import/{body['import_id']}/export.xlsx").status_code == 422


def test_every_export_ends_with_the_disclaimer_in_the_language_asked() -> None:
    rows = list(
        csv.reader(io.StringIO("".join(csv_stream([], "fr")).lstrip("\ufeff")), delimiter=";")
    )
    assert rows[-2:] == [[], [DISCLAIMER["fr"]]]
    last = json.loads("".join(jsonl_stream([], "fr")).splitlines()[-1])
    assert last == {"record_type": "disclaimer", "text": DISCLAIMER["fr"]}
