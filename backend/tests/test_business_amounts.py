# SPDX-License-Identifier: EUPL-1.2
"""Consistency of the amounts between arrangements and providers (CL-44, decisions of PO-35)."""

import copy

from contracts.check_report import load_checks
from tests.cases.golden import load_golden
from tests.cases.mutations import set_where
from tests.test_import_api import post

PROVIDER_A = "529900KIWVWB8P3VEK25"


def findings(client, edit=None) -> dict[str, dict]:
    package = copy.deepcopy(load_golden())
    if edit:
        edit(package)
    body = post(client, package.name, package.to_zip()).json()
    return {m["code"]: m for m in body["messages"]}


def test_the_check_has_no_effect_on_the_scores() -> None:
    (check,) = [c for c in load_checks() if c.id == "dq_amounts"]
    assert check.codes == ("DQ-014", "DQ-015")
    assert check.weight == 0 and check.scored is False


def test_total_lower_than_the_sum_of_the_arrangements(client) -> None:
    clean = findings(client)
    assert "DQ-014" not in clean and "DQ-015" not in clean

    found = findings(
        client, lambda p: set_where(p, "B_05.01", "c0010", PROVIDER_A, "c0100", "1000")
    )
    message = found["DQ-014"]
    assert message["severity"] == "INFO" and message["profile"] == "EXPERT"
    (place,) = message["occurrences"]
    assert (place["table"], place["column"], place["value"]) == ("B_05.01", "c0100", "1000")
    assert (place["target_table"], place["target_column"]) == ("B_02.01", "c0050")


def test_a_higher_total_is_allowed(client) -> None:
    edit = lambda p: set_where(p, "B_05.01", "c0010", PROVIDER_A, "c0100", "9999999")  # noqa: E731
    assert "DQ-014" not in findings(client, edit)


def test_another_currency_is_reported_and_not_compared(client) -> None:
    def edit(package) -> None:
        set_where(package, "B_05.01", "c0010", PROVIDER_A, "c0090", "eba_CU:USD")
        set_where(package, "B_05.01", "c0010", PROVIDER_A, "c0100", "1")

    found = findings(client, edit)
    assert "DQ-014" not in found
    assert found["DQ-015"]["occurrences"][0]["column"] == "c0040"


def test_an_amount_that_is_not_a_number_does_not_stop_the_rule(client) -> None:
    edit = lambda p: set_where(p, "B_05.01", "c0010", PROVIDER_A, "c0100", "NaN")  # noqa: E731
    found = findings(client, edit)
    assert "DQ-014" not in found
