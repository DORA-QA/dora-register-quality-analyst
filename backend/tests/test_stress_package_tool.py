# SPDX-License-Identifier: EUPL-1.2
"""The load-test package builder (30/10/2026) makes a consistent, fictitious register."""

import io
import zipfile

from contracts.identifiers import LEI_OK, analyse_lei
from tools import build_stress_package as tool


def test_fictitious_leis_are_valid_and_distinct():
    leis = [tool.fictitious_lei(n) for n in (0, 1, 35, 36, 499_999, 10**9)]
    assert all(analyse_lei(lei).problem == LEI_OK for lei in leis)
    assert all(lei.startswith("ZZZZ") for lei in leis)
    assert len(set(leis)) == len(leis)


def test_small_package_has_the_rows_requested_and_stays_consistent(client):
    name, content, counts = tool.build(40)
    assert counts["B_05.01"] == 40
    assert counts["B_02.02"] == 17 + (40 - 12)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert any(n.endswith("reports/b_02.02.csv") for n in archive.namelist())

    body = client.post("/api/import", files={"file": (name, content)}).json()
    # Only the findings admitted for the golden: the added arrangements are complete.
    assert {m["code"] for m in body["messages"]} == {"REL-007", "DQ-006", "REL-017"}
