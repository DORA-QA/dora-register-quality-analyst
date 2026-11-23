# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 5: chains of sub-contracting (REL-018 to REL-021, BUS-018, BUS-019).

For each check (brief §17.1): compliant case, non-compliant case, limit case, absent table,
empty value, documented exception, location of the occurrences, origin and status.
"""

import pytest

from contracts.check_report import load_registry
from contracts.dataset import PackageMetadata, RoIDataset
from contracts.messages import load_catalog
from rules.business.chains import chain_rules
from rules.engine import RulesEngine
from tests.test_technical_rules import frame

EF = "529900P784EKW7VFMQ21"
IG, IG2 = "5299003U9L1RY87FL751", "529900D18SWZVAN3CV11"
LEI_A, LEI_B, LEI_C = "529900KIWVWB8P3VEK25", "529900B72OC154SWIT02", "529900JULHLZDL9AS417"
LEI, NATIONAL = "eba_qCO:qx2000", "eba_qCO:qx2001"
YES, NO = "eba_BT:x28", "eba_BT:x29"
NATURAL, LEGAL = "eba_CT:x213", "eba_CT:x212"
S = "eba_TA:S15"


def chain(contract="C1", rank="1", provider=LEI_A, recipient=None, service=S, kind=LEI, rkind=None):
    return {
        "c0010": contract,
        "c0020": service,
        "c0030": provider,
        "c0040": kind,
        "c0050": rank,
        "c0060": recipient if recipient is not None else provider,
        "c0070": rkind or kind,
    }


def run(b0502, b0203=None, b0102=None, critical=None, b0501=None):
    found = {"B_05.02": frame("B_05.02", *b0502)} if b0502 is not None else {}
    if b0203 is not None:
        found["B_02.03"] = frame("B_02.03", *b0203)
    if b0102 is not None:
        found["B_01.02"] = frame("B_01.02", *b0102)
    if b0501 is not None:
        found["B_05.01"] = frame("B_05.01", *b0501)
    if critical is not None:
        found["B_06.01"] = frame(
            "B_06.01",
            {"c0010": "F1", "c0040": EF, "c0050": YES if critical else NO},
        )
        found["B_02.02"] = frame(
            "B_02.02", {"c0010": "C1", "c0020": EF, "c0030": LEI_A, "c0050": "F1", "c0060": S}
        )
    return RulesEngine(chain_rules()).run(RoIDataset("ZIP", PackageMetadata(), found)).messages


def codes(*args, **kwargs):
    return sorted(m.code for m in run(*args, **kwargs))


def finding(code, *args, **kwargs):
    return next(m for m in run(*args, **kwargs) if m.code == code)


def group(*entities):
    return [{"c0010": code, "c0040": kind} for code, kind in entities]


# ------------------------------------------------------------------ compliant and absent
def test_a_complete_chain_raises_nothing():
    rows = [chain(), chain(rank="2", provider=LEI_B, recipient=LEI_A)]
    assert codes(rows) == []


def test_absent_tables_raise_nothing():
    messages = RulesEngine(chain_rules()).run(RoIDataset("ZIP", PackageMetadata(), {}))
    assert messages.messages == []


def test_parallel_providers_of_one_rank_are_legitimate():
    """1, 1, 2 can be legitimate (brief §10.3)."""
    rows = [
        chain(),
        chain(provider=LEI_B),
        chain(rank="2", provider=LEI_C, recipient=LEI_B),
    ]
    assert codes(rows) == []


# ------------------------------------------------------------------ REL-018
def test_rel_018_no_rank_one_for_a_pair():
    found = finding("REL-018", [chain(rank="2", provider=LEI_B, recipient=LEI_A)])
    (place,) = found.occurrences
    assert (place.table, place.row, place.column) == ("B_05.02", 1, "c0050")


def test_rel_018_is_per_pair_of_arrangement_and_service():
    rows = [chain(), chain(rank="2", provider=LEI_B, recipient=LEI_A, service="eba_TA:S14")]
    assert "REL-018" in codes(rows)


def test_rel_018_arrangement_of_b_02_02_without_any_chain_row():
    rows = RulesEngine(chain_rules()).run(
        RoIDataset(
            "ZIP",
            PackageMetadata(),
            {
                "B_05.02": frame("B_05.02", chain()),
                "B_02.02": frame("B_02.02", {"c0010": "C9", "c0060": S}),
            },
        )
    )
    (place,) = next(m for m in rows.messages if m.code == "REL-018").occurrences
    assert (place.table, place.target_table) == ("B_02.02", "B_05.02")


def test_rel_018_intra_group_exception_by_b_02_03():
    """P8: an arrangement linked by B_02.03.0020 starts at rank 2."""
    rows = [chain("C1", provider=IG), chain("C2", rank="2", provider=LEI_B, recipient=IG)]
    links = [{"c0010": "C1", "c0020": "C2"}]
    assert "REL-018" not in codes(rows, links, group((IG, "eba_CT:x317")))
    assert "REL-018" in codes(rows)


def test_rel_018_arrangement_in_the_main_column_is_not_exempt():
    rows = [chain("C1", rank="2", provider=LEI_B, recipient=IG)]
    assert "REL-018" in codes(rows, [{"c0010": "C1", "c0020": "C2"}])


# ------------------------------------------------------------------ REL-019
@pytest.mark.parametrize(
    ("rank", "recipient", "broken"),
    [
        ("2", LEI_A, False),
        ("2", LEI_C, True),
        ("3", LEI_A, True),  # rank 2 does not exist
        ("2", "", False),  # empty value: a mandatory-field business
    ],
)
def test_rel_019_continuity(rank, recipient, broken):
    rows = [chain(), chain(rank=rank, provider=LEI_B, recipient=recipient)]
    assert ("REL-019" in codes(rows)) is broken


def test_rel_019_location_is_the_recipient_cell():
    found = finding("REL-019", [chain(), chain(rank="2", provider=LEI_B, recipient=LEI_C)])
    (place,) = found.occurrences
    assert (place.table, place.row, place.column, place.value) == ("B_05.02", 2, "c0060", LEI_C)


def test_rel_019_rank_not_a_number_is_ignored():
    assert "REL-019" not in codes([chain(), chain(rank="deux", provider=LEI_B, recipient=LEI_C)])


def test_rel_019_continuity_is_per_service_type():
    rows = [chain(), chain(rank="2", provider=LEI_B, recipient=LEI_A, service="eba_TA:S14")]
    assert "REL-019" in codes(rows)


def test_rel_019_rank_two_of_a_linked_arrangement_is_exempt():
    rows = [chain("C2", rank="2", provider=LEI_B, recipient=IG)]
    assert "REL-019" not in codes(rows, [{"c0010": "C1", "c0020": "C2"}])


def test_rel_019_rank_three_of_a_linked_arrangement_is_checked():
    rows = [chain("C2", rank="3", provider=LEI_C, recipient=IG)]
    assert "REL-019" in codes(rows, [{"c0010": "C1", "c0020": "C2"}])


# ------------------------------------------------------------------ BUS-018
def test_bus_018_rank_one_recipient_differs_from_the_provider():
    found = finding("BUS-018", [chain(recipient=EF)])
    (place,) = found.occurrences
    assert (place.row, place.column, place.value) == (1, "c0060", EF)


def test_bus_018_type_of_code_differs():
    assert "BUS-018" in codes([chain(rkind=NATIONAL)])


def test_bus_018_empty_recipient_is_not_this_rule():
    assert "BUS-018" not in codes([chain(recipient="")])


def test_bus_018_rank_two_is_not_concerned():
    assert "BUS-018" not in codes([chain(), chain(rank="2", provider=LEI_B, recipient=LEI_A)])


# ------------------------------------------------------------------ REL-020, REL-021
def test_rel_020_main_arrangement_without_intra_group_provider():
    found = finding(
        "REL-020",
        [chain("C1", provider=LEI_A)],
        [{"c0010": "C1", "c0020": "C2"}],
        group((IG, "eba_CT:x317")),
    )
    assert found.occurrences[0].column == "c0030"


def test_rel_020_intra_group_recipient_without_link():
    rows = [chain("C2", rank="2", provider=LEI_B, recipient=IG)]
    assert "REL-020" in codes(rows, [], group((IG, "eba_CT:x317")))


def test_rel_020_consistent_mechanism():
    rows = [chain("C1", provider=IG), chain("C2", rank="2", provider=LEI_B, recipient=IG)]
    links = [{"c0010": "C1", "c0020": "C2"}]
    assert codes(rows, links, group((IG, "eba_CT:x317"))) == []


def test_rel_020_without_b_01_02_nothing_is_decided():
    rows = [chain("C1", provider=LEI_A)]
    assert "REL-020" not in codes(rows, [{"c0010": "C1", "c0020": "C2"}])


def test_rel_021_linked_arrangement_with_intra_group_providers_only():
    rows = [chain("C1", provider=IG), chain("C2", rank="2", provider=IG2, recipient=IG)]
    found = finding(
        "REL-021",
        rows,
        [{"c0010": "C1", "c0020": "C2"}],
        group((IG, "eba_CT:x317"), (IG2, "eba_CT:x317")),
    )
    (place,) = found.occurrences
    assert (place.table, place.column) == ("B_02.03", "c0020")


def test_rel_021_a_provider_outside_the_group_is_enough():
    rows = [chain("C1", provider=IG), chain("C2", rank="2", provider=LEI_B, recipient=IG)]
    links = [{"c0010": "C1", "c0020": "C2"}]
    assert "REL-021" not in codes(rows, links, group((IG, "eba_CT:x317")))


# ------------------------------------------------------------------ BUS-019
def providers(kind, person=LEGAL):
    return [{"c0010": LEI_A, "c0020": kind, "c0070": person}]


def test_bus_019_national_code_in_a_critical_chain():
    found = finding("BUS-019", [chain(kind=NATIONAL)], critical=True, b0501=providers(NATIONAL))
    (place,) = found.occurrences
    assert (place.table, place.row, place.column) == ("B_05.02", 1, "c0040")


@pytest.mark.parametrize(
    ("kind", "person", "critical", "raised"),
    [
        (NATIONAL, LEGAL, True, True),
        (NATIONAL, NATURAL, True, False),  # natural person excepted
        (LEI, LEGAL, True, False),
        ("eba_qCO:qx2002", LEGAL, True, False),  # EUID
        (NATIONAL, LEGAL, False, False),  # not critical
        ("", LEGAL, True, False),  # empty value
    ],
)
def test_bus_019_cases(kind, person, critical, raised):
    rows = [chain(kind=kind or NATIONAL)]
    result = codes(rows, critical=critical, b0501=providers(kind, person))
    assert ("BUS-019" in result) is raised


def test_bus_019_without_functions_nothing_is_decided():
    assert "BUS-019" not in codes([chain(kind=NATIONAL)], b0501=providers(NATIONAL))


# ------------------------------------------------------------------ origin and status
EXPECTED = {
    "REL-018": ("MAJOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-019": ("MAJOR", "OFFICIAL", "PROVISIONAL"),
    "BUS-018": ("BLOCKER", "PO_VALIDATED", "PROVISIONAL"),
    "REL-020": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "REL-021": ("MINOR", "PO_VALIDATED", "PO_VALIDATED"),
    "BUS-019": ("MAJOR", "OFFICIAL", "PROVISIONAL"),
}


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_severity_origin_and_status(code):
    severity, origin, status = EXPECTED[code]
    entry = next(e for e in load_registry() if e["code"] == code)
    assert load_catalog()[code]["severity"] == severity
    assert (entry["origin"], entry["severity_status"]) == (origin, status)
