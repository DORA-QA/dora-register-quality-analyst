# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 7: concentration indicators (brief §13), returned by the API without display."""

import pytest

from contracts.dataset import PackageMetadata, RoIDataset
from indicators import concentration as module
from indicators.concentration import concentration
from tests.test_technical_rules import frame

EF, FE2 = "529900P784EKW7VFMQ21", "529900WFW9ZXG409UL36"
A, B, C = "529900KIWVWB8P3VEK25", "197697980", "426322228"
YES, NO = "eba_BT:x28", "eba_BT:x29"


def service(provider, function="F1", entity=EF, kind="eba_TA:S15", country="eba_GA:FR"):
    return {
        "c0010": f"C-{provider}",
        "c0020": entity,
        "c0030": provider,
        "c0040": "eba_qCO:qx2000",
        "c0050": function,
        "c0060": kind,
        "c0130": country,
    }


def dataset(services, functions=None, providers=None):
    tables = {"B_02.02": frame("B_02.02", *services)}
    if functions is not None:
        tables["B_06.01"] = frame("B_06.01", *functions)
    if providers is not None:
        tables["B_05.01"] = frame("B_05.01", *providers)
    return RoIDataset("ZIP", PackageMetadata(), tables)


def function(code, critical=YES, entity=EF):
    return {"c0010": code, "c0040": entity, "c0050": critical}


def provider(code, name, country="eba_GA:FR"):
    return {"c0010": code, "c0020": "eba_qCO:qx2000", "c0050": name, "c0080": country}


def test_nothing_to_measure_without_b_02_02():
    assert concentration(RoIDataset("ZIP", PackageMetadata(), {})) is None
    assert concentration(dataset([])) is None


def test_shares_and_hhi_of_the_direct_providers():
    result = concentration(dataset([service(A), service(A), service(A), service(B)]))
    assert (result.rows, result.providers_count) == (4, 2)
    assert [(p.code, p.rows, p.share) for p in result.providers] == [(A, 3, 0.75), (B, 1, 0.25)]
    assert result.hhi == 6250.0  # 75² + 25²


def test_a_single_provider_gives_the_maximum_hhi():
    assert concentration(dataset([service(A)])).hhi == 10000.0


def test_critical_functions_and_single_provider():
    services = [service(A, "F1"), service(B, "F1"), service(A, "F2"), service(C, "F3")]
    functions = [function("F1"), function("F2"), function("F3", NO), function("F4")]
    result = concentration(dataset(services, functions))
    assert result.critical_functions == 3  # F1, F2, F4
    assert result.critical_functions_without_provider == 1  # F4
    single = [(f.function, f.entity, f.provider) for f in result.single_provider_critical_functions]
    assert single == [("F2", EF, A)]
    by_code = {p.code: p for p in result.providers}
    assert (by_code[A].critical_functions, by_code[A].critical_share) == (2, 1.0)
    assert (by_code[B].critical_functions, by_code[B].critical_share) == (1, 0.5)
    assert by_code[C].critical_functions == 0


def test_criticality_is_per_entity():
    """F1 is critical for EF only: the F1 of FE2 is not counted (key: identifier and LEI)."""
    result = concentration(dataset([service(A, "F1", FE2)], [function("F1")]))
    assert result.providers[0].critical_functions == 0
    assert result.critical_functions_without_provider == 1


def test_breakdowns_by_country_and_type_of_service():
    services = [
        service(A, kind="eba_TA:S14"),
        service(B, kind="eba_TA:S14", country="eba_GA:DE"),
        service(C, kind="eba_TA:S19", country=""),
    ]
    providers = [provider(A, "A", "eba_GA:US"), provider(B, "B", "eba_GA:US")]
    result = concentration(dataset(services, providers=providers))
    head_office = {i.key: (i.rows, i.providers) for i in result.by_headquarters_country.items}
    assert head_office == {"eba_GA:US": (2, 2), None: (1, 1)}  # C is not in B_05.01
    provision = {i.key: i.rows for i in result.by_provision_country.items}
    assert provision == {"eba_GA:FR": 1, "eba_GA:DE": 1, None: 1}
    assert [(i.key, i.share) for i in result.by_service_type.items] == [
        ("eba_TA:S14", 0.6667),
        ("eba_TA:S19", 0.3333),
    ]
    assert {p.code: p.name for p in result.providers}[A] == "A"


def test_long_lists_are_cut_and_counted(monkeypatch):
    monkeypatch.setattr(module, "MAX_ITEMS", 2)
    result = concentration(dataset([service(p) for p in (A, A, B, C, "D")]))
    assert [p.code for p in result.providers] == [A, B]
    assert result.providers_not_shown == 2
    assert sum(p.rows for p in result.providers) == 3


def test_amounts_are_not_computed_yet():
    assert concentration(dataset([service(A)])).notes == ["amounts: not computed (PO-35)"]


@pytest.mark.parametrize("broken", [RuntimeError, KeyError])
def test_an_error_never_stops_the_import(monkeypatch, broken):
    from api.services import import_service

    def explode(_):
        raise broken("x")

    monkeypatch.setattr(import_service, "concentration", explode)
    # Since 0.8.2 the state says why nothing is shown (brief of the Sprint 4, §13).
    assert import_service._indicators(dataset([service(A)])) == (None, "INSUFFICIENT_DATA")


def test_state_of_the_indicators():
    from api.services import import_service

    assert import_service._indicators(dataset([]))[1] == "NOT_APPLICABLE"
    assert import_service._indicators(dataset([service(A)]))[1] == "EVALUATED"
