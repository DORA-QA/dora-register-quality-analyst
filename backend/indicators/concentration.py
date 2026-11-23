# SPDX-License-Identifier: EUPL-1.2
"""Concentration indicators (Sprint 3, brief §13; restitution §6). API only, no display, no score.

Computed on B_02.02 (one row per arrangement, entity, provider, function, type of service and
locations), with B_06.01 for the criticality of the functions and B_05.01 for the country of the
providers. Formulas and dimensions: ``docs/concentration.md``.

- providers: share of each direct provider (B_02.02.0030) in the rows, and the critical or
  important functions it supports; Herfindahl-Hirschman index (HHI) on the shares of rows.
- critical functions resting on a single direct provider.
- breakdown by country of the head office of the provider (B_05.01.0080), by country of
  provision of the service (B_02.02.0130) and by type of service (B_02.02.0060).

Amounts (annual cost per provider) are left out until the PO decides how to add them (PO-35).
Values are reported as found; nothing is corrected or merged, nothing is logged.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from contracts.dataset import RoIDataset
from contracts.json_types import Row
from contracts.messages import clip
from contracts.tables import by_code, rows

YES = "eba_BT:x28"
MAX_ITEMS = 50  # longest list returned per dimension; the rest is counted in ``not_shown``


@dataclass(frozen=True)
class Share:
    key: str | None
    rows: int
    share: float
    providers: int | None = None


@dataclass(frozen=True)
class ProviderShare:
    code: str | None
    code_type: str | None
    name: str | None
    rows: int
    share: float
    critical_functions: int
    critical_share: float


@dataclass(frozen=True)
class SingleProviderFunction:
    function: str
    entity: str
    provider: str | None


@dataclass(frozen=True)
class Breakdown:
    items: list[Share]
    not_shown: int = 0


@dataclass(frozen=True)
class Concentration:
    basis: str
    rows: int
    providers_count: int
    hhi: float
    providers: list[ProviderShare]
    providers_not_shown: int
    critical_functions: int
    critical_functions_without_provider: int
    single_provider_critical_functions: list[SingleProviderFunction]
    single_provider_not_shown: int
    by_headquarters_country: Breakdown
    by_provision_country: Breakdown
    by_service_type: Breakdown
    notes: list[str] = field(default_factory=list)


def _ratio(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def _breakdown(
    counts: Counter[str | None],
    total: int,
    providers: dict[str | None, set[str | None]] | None = None,
) -> Breakdown:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0] or ""))
    items = [
        Share(
            _shown(key), n, _ratio(n, total), len(providers[key]) if providers is not None else None
        )
        for key, n in ordered[:MAX_ITEMS]
    ]
    return Breakdown(items, max(0, len(ordered) - MAX_ITEMS))


def _attribute(directory: dict[str, Row], code: str | None, column: str) -> str | None:
    """A column of a provider of B_05.01, None when the provider is not declared there."""
    row = directory.get(code) if code is not None else None
    return None if row is None else _shown(row.get(column))


def _shown(value: str | None) -> str | None:
    """A register value as copied into the answer: cut when absurdly long (red team RT-18)."""
    return None if value is None else clip(value)


def concentration(dataset: RoIDataset) -> Concentration | None:
    """None when B_02.02 is absent or empty: there is nothing to measure."""
    services = list(
        rows(dataset, "B_02.02", "c0010", "c0020", "c0030", "c0040", "c0050", "c0060", "c0130")
    )
    if not services:
        return None
    critical = {
        (f["c0010"], f["c0040"])
        for f in rows(dataset, "B_06.01", "c0010", "c0040", "c0050")
        if f["c0010"] and f["c0040"] and f["c0050"] == YES
    }
    directory = by_code(dataset, "B_05.01", "c0010", "c0020", "c0050", "c0080")
    total = len(services)

    per_provider: Counter[str | None] = Counter()
    code_types: dict[str | None, str | None] = {}
    supported: defaultdict[str | None, set[tuple[str, str]]] = defaultdict(set)
    providers_of_function: defaultdict[tuple[str, str], set[str | None]] = defaultdict(set)
    hq_counts: Counter[str | None] = Counter()
    hq_providers: defaultdict[str | None, set[str | None]] = defaultdict(set)
    provision: Counter[str | None] = Counter()
    service_types: Counter[str | None] = Counter()
    for s in services:
        provider = s["c0030"]
        per_provider[provider] += 1
        code_types.setdefault(provider, s["c0040"])
        function = (s["c0050"], s["c0020"])
        if function in critical:
            supported[provider].add(function)
            providers_of_function[function].add(provider)
        country = (directory.get(provider) or {}).get("c0080")
        hq_counts[country] += 1
        hq_providers[country].add(provider)
        provision[s["c0130"]] += 1
        service_types[s["c0060"]] += 1

    covered = len(providers_of_function)
    ordered = sorted(per_provider.items(), key=lambda item: (-item[1], item[0] or ""))
    providers = [
        ProviderShare(
            code=_shown(code),
            code_type=_shown(code_types.get(code)) or _attribute(directory, code, "c0020"),
            name=_attribute(directory, code, "c0050"),
            rows=n,
            share=_ratio(n, total),
            critical_functions=len(supported[code]),
            critical_share=_ratio(len(supported[code]), covered),
        )
        for code, n in ordered[:MAX_ITEMS]
    ]
    hhi = round(sum((100 * n / total) ** 2 for n in per_provider.values()), 1)
    single = sorted(
        (
            SingleProviderFunction(clip(function), clip(entity), _shown(next(iter(found))))
            for (function, entity), found in providers_of_function.items()
            if len(found) == 1
        ),
        key=lambda item: (item.function, item.entity),
    )
    return Concentration(
        basis="B_02.02",
        rows=total,
        providers_count=len(per_provider),
        hhi=hhi,
        providers=providers,
        providers_not_shown=max(0, len(ordered) - MAX_ITEMS),
        critical_functions=len(critical),
        critical_functions_without_provider=len(critical) - covered,
        single_provider_critical_functions=single[:MAX_ITEMS],
        single_provider_not_shown=max(0, len(single) - MAX_ITEMS),
        by_headquarters_country=_breakdown(hq_counts, total, hq_providers),
        by_provision_country=_breakdown(provision, total),
        by_service_type=_breakdown(service_types, total),
        notes=["amounts: not computed (PO-35)"],
    )
