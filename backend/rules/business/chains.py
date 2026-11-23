# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 5: chains of sub-contracting, B_05.02 (brief §10).

REL-018  no rank 1 for a pair (arrangement, type of ICT service) (§10.1; P8 exception)
REL-019  break of the chain: a rank n >= 2 whose recipient is no provider of rank n-1 (§10.3)
BUS-018  rank 1 whose recipient differs from the provider (§10.4, P2, BLOCKER provisional)
REL-020  intra-group mechanism inconsistent between B_02.03 and the intra-group providers
         of B_01.02 (§10.6, P8)
REL-021  intra-group arrangement linked by B_02.03 to a third-party arrangement without any
         provider outside the group (§10.6)
BUS-019  provider of a chain supporting a critical function identified by neither a LEI nor
         an EUID, natural persons excepted (§10.7)

The intra-group exception (P8): an arrangement cited in B_02.03.0020 is linked to an
intra-group arrangement; its rank 1 is carried by the intra-group arrangement, so its rows
start at rank 2 and its rank 2 may name the intra-group provider as recipient.
Intra-group providers are those typed ``x317`` in B_01.02.
"""

from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from rules.business.common import INTRA_GROUP_PROVIDER, ROW_COLUMN, by_code, rows
from rules.business.functions import _Functions
from rules.business.providers import EUID_TYPE, LEI_TYPE
from rules.technical.locations import describe

NATURAL_PERSON = "eba_CT:x213"


def _finding(code: str, table: str, places: list[Occurrence], lines: list[str], **params):
    message = make_message(code, details=describe(lines), table=table, count=len(lines), **params)
    return with_occurrences(message, places)


def _place(table: str, row: dict, column: str, **target) -> Occurrence:
    return Occurrence(
        table=table, row=row[ROW_COLUMN], column=column, value=row.get(column), **target
    )


def _rank(value: str | None) -> int | None:
    try:
        number = int(value) if value else None
    except ValueError:
        return None
    return number if number is not None and number >= 1 else None


class _Chains:
    """B_05.02 with the intra-group links of B_02.03 and the intra-group providers."""

    def __init__(self, dataset: RoIDataset) -> None:
        self.rows = [
            {**r, "rank": _rank(r["c0050"])}
            for r in rows(
                dataset, "B_05.02", "c0010", "c0020", "c0030", "c0040", "c0050", "c0060", "c0070"
            )
        ]
        self.links = list(rows(dataset, "B_02.03", "c0010", "c0020"))
        self.main = {link["c0010"] for link in self.links if link["c0010"]}
        self.linked = {link["c0020"] for link in self.links if link["c0020"]}
        entities = by_code(dataset, "B_01.02", "c0010", "c0040")
        self.intra_group = {c for c, e in entities.items() if e["c0040"] == INTRA_GROUP_PROVIDER}
        self.has_chains = "B_05.02" in dataset.tables
        self.in_group_links = self.linked | self.main
        # Indexes built once: the rules look rows up by arrangement (brief §17.5, performance).
        self._by_pair: dict[tuple, list[dict]] = {}
        self.by_contract: dict[str | None, list[dict]] = {}
        for r in self.rows:
            self._by_pair.setdefault((r["c0010"], r["c0020"]), []).append(r)
            self.by_contract.setdefault(r["c0010"], []).append(r)

    def of(self, contract: str, service: str) -> list[dict]:
        return self._by_pair.get((contract, service), [])


class MissingRankOneRule:
    """REL-018: a rank 1 for every pair (arrangement, type of service)."""

    id = "REL-018"
    codes = ("REL-018",)

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        chains = _Chains(dataset)
        if not chains.has_chains:
            return []
        first: dict[tuple[str, str], Occurrence] = {}
        ranked: set[tuple[str, str]] = set()
        for r in chains.rows:
            if r["c0010"] and r["c0020"]:
                key = (r["c0010"], r["c0020"])
                first.setdefault(key, _place("B_05.02", r, "c0050"))
                if r["rank"] == 1:
                    ranked.add(key)
        for s in rows(dataset, "B_02.02", "c0010", "c0060"):
            if s["c0010"] and s["c0060"]:
                key = (s["c0010"], s["c0060"])
                first.setdefault(
                    key,
                    _place(
                        "B_02.02",
                        s,
                        "c0060",
                        target_table="B_05.02",
                        target_column="c0050",
                        side="source",
                    ),
                )
        missing = [k for k in first if k not in ranked and k[0] not in chains.linked]
        if not missing:
            return []
        places = [first[k] for k in missing]
        lines = [f"{contract!r} / {service}" for contract, service in missing]
        return [_finding(self.id, "B_05.02", places, lines)]


class ChainContinuityRule:
    """REL-019 (break of the chain), BUS-018 (recipient of rank 1)."""

    id = "REL-019"
    codes = ("BUS-018", "REL-019")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        chains = _Chains(dataset)
        found: list[ValidationMessage] = []
        broken_places, broken_lines, first_places, first_lines = [], [], [], []
        for r in chains.rows:
            if r["rank"] is None or not r["c0010"] or not r["c0020"]:
                continue
            if r["rank"] == 1:
                differs = r["c0060"] and r["c0030"] and r["c0060"] != r["c0030"]
                if differs or (r["c0070"] and r["c0040"] and r["c0070"] != r["c0040"]):
                    first_places.append(_place("B_05.02", r, "c0060"))
                    first_lines.append(
                        f"#{r[ROW_COLUMN]} · {r['c0010']!r} : B_05.02.0030 = {r['c0030']!r}, "
                        f"B_05.02.0060 = {r['c0060']!r}"
                    )
                continue
            if r["rank"] == 2 and r["c0010"] in chains.linked:
                continue  # P8: the rank 1 is carried by the intra-group arrangement
            if not r["c0060"]:
                continue
            parents = {
                p["c0030"]
                for p in chains.of(r["c0010"], r["c0020"])
                if p["rank"] == r["rank"] - 1 and p["c0030"]
            }
            if r["c0060"] not in parents:
                broken_places.append(_place("B_05.02", r, "c0060"))
                broken_lines.append(
                    f"#{r[ROW_COLUMN]} · {r['c0010']!r}, B_05.02.0050 = {r['rank']} : "
                    f"B_05.02.0060 = {r['c0060']!r} ∉ B_05.02.0030 ({r['rank'] - 1})"
                )
        if broken_lines:
            found.append(_finding("REL-019", "B_05.02", broken_places, broken_lines))
        if first_lines:
            found.append(_finding("BUS-018", "B_05.02", first_places, first_lines))
        return found


class IntraGroupChainRule:
    """REL-020 (B_02.03 against B_01.02), REL-021 (first provider outside the group)."""

    id = "REL-020"
    codes = ("REL-020", "REL-021")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        chains = _Chains(dataset)
        if not chains.has_chains:
            return []
        inconsistent: list[tuple[Occurrence, str]] = []
        for r in chains.rows:
            if r["rank"] == 1 and r["c0010"] in chains.main and r["c0030"]:
                if chains.intra_group and r["c0030"] not in chains.intra_group:
                    inconsistent.append(
                        (
                            _place(
                                "B_05.02",
                                r,
                                "c0030",
                                target_table="B_01.02",
                                target_column="c0010",
                                side="source",
                            ),
                            f"#{r[ROW_COLUMN]} · {r['c0010']!r} ∈ B_02.03.0010 : "
                            f"B_05.02.0030 = {r['c0030']!r} ∉ B_01.02 (x317)",
                        )
                    )
            elif (
                r["rank"] is not None
                and r["rank"] >= 2
                and r["c0060"] in chains.intra_group
                and r["c0010"] not in chains.in_group_links
            ):
                inconsistent.append(
                    (
                        _place(
                            "B_05.02",
                            r,
                            "c0060",
                            target_table="B_02.03",
                            target_column="c0010",
                            side="source",
                        ),
                        f"#{r[ROW_COLUMN]} · {r['c0010']!r} : B_05.02.0060 = "
                        f"{r['c0060']!r} (x317) ∉ B_02.03",
                    )
                )
        found: list[ValidationMessage] = []
        if inconsistent:
            found.append(
                _finding(
                    "REL-020",
                    "B_05.02",
                    [p for p, _ in inconsistent],
                    [line for _, line in inconsistent],
                )
            )
        places, lines = [], []
        for link in chains.links:
            target = link["c0020"]
            if not target or not chains.intra_group:
                continue
            members = chains.by_contract.get(target, [])
            if members and all(r["c0030"] in chains.intra_group for r in members if r["c0030"]):
                places.append(
                    _place(
                        "B_02.03",
                        link,
                        "c0020",
                        target_table="B_05.02",
                        target_column="c0030",
                        side="source",
                    )
                )
                lines.append(f"#{link[ROW_COLUMN]} · {target!r} : B_05.02.0030 ⊂ B_01.02 (x317)")
        if lines:
            found.append(_finding("REL-021", "B_02.03", places, lines))
        return found


class CriticalChainIdentifierRule:
    """BUS-019: LEI or EUID for every provider of a chain supporting a critical function."""

    id = "BUS-019"
    codes = ("BUS-019",)

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        chains = _Chains(dataset)
        data = _Functions(dataset)
        if not chains.rows or not data.services:
            return []
        providers = by_code(dataset, "B_05.01", "c0010", "c0020", "c0070")
        critical = {(s["c0010"], s["c0060"]) for s in data.services if data.is_critical(s) is True}
        places, lines, seen = [], [], set()
        for r in chains.rows:
            provider = providers.get(r["c0030"]) if r["c0030"] else None
            if (r["c0010"], r["c0020"]) not in critical or provider is None:
                continue
            kind = provider["c0020"]
            if not kind or kind in (LEI_TYPE, EUID_TYPE) or provider["c0070"] == NATURAL_PERSON:
                continue
            if r["c0030"] in seen:
                continue
            seen.add(r["c0030"])
            places.append(_place("B_05.02", r, "c0040"))
            lines.append(f"#{r[ROW_COLUMN]} · {r['c0010']!r} : {r['c0030']!r} ({kind})")
        if not lines:
            return []
        return [_finding(self.id, "B_05.02", places, lines)]


def chain_rules() -> list:
    return [
        MissingRankOneRule(),
        ChainContinuityRule(),
        IntraGroupChainRule(),
        CriticalChainIdentifierRule(),
    ]
