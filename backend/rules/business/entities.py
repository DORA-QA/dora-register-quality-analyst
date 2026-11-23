# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 1: entities of the group and ultimate parents (brief §5, decisions P6, P8).

REL-001  the entity maintaining the register (B_01.01) is listed in B_01.02 (ITS, B_01.02)
REL-002  same LEI, names different after normalisation (B_01.01/B_01.02, B_01.02/B_05.01)
REL-003  same LEI, names equal after normalisation but written differently (advice)
REL-004  same LEI, different countries (same pairs)
REL-005  ultimate parent of an intra-group provider outside the chain of its parents
BUS-001  more than one ultimate parent (x53) in B_01.02
BUS-002  chain of direct parents with a cycle, or not ending on the ultimate parent
BUS-003  type of code of a provider's ultimate parent different from that parent's own type
BUS-004  ultimate parent of a provider that is not its own ultimate parent
BUS-005  dates of an entity inconsistent (integration after update, deletion before integration)

Two existing values in conflict give two occurrences, one per side (brief §14.2).
"""

from collections.abc import Iterable

from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from contracts.naming import field_reference
from rules.business.common import (
    INTRA_GROUP_PROVIDER,
    ROW_COLUMN,
    ULTIMATE_PARENT,
    by_code,
    normalise_name,
    rows,
)
from rules.technical.locations import describe

OPEN_DATE = "9999-12-31"


def _finding(code: str, table: str, places: list[Occurrence], lines: list[str], **params):
    message = make_message(code, details=describe(lines), table=table, count=len(lines), **params)
    return with_occurrences(message, places)


def _pair(
    source: tuple[str, dict, str], target: tuple[str, dict, str]
) -> tuple[list[Occurrence], str]:
    """Two occurrences for one conflict, and the line shown in ``details``."""
    (s_table, s_row, s_col), (t_table, t_row, t_col) = source, target
    places = [
        Occurrence(
            table=s_table,
            row=s_row[ROW_COLUMN],
            column=s_col,
            value=s_row[s_col],
            target_table=t_table,
            target_column=t_col,
            side="source",
        ),
        Occurrence(
            table=t_table, row=t_row[ROW_COLUMN], column=t_col, value=t_row[t_col], side="target"
        ),
    ]
    line = (
        f"#{s_row[ROW_COLUMN]} · {field_reference(s_table, s_col)} {s_row[s_col]!r} ≠ "
        f"{field_reference(t_table, t_col)} {t_row[t_col]!r} (#{t_row[ROW_COLUMN]})"
    )
    return places, line


# Pairs of references that describe the same entity: (source, name, country) -> (target, ...).
PAIRS = (
    (("B_01.01", "c0010", "c0020", "c0030"), ("B_01.02", "c0010", "c0020", "c0030")),
    (("B_01.02", "c0010", "c0020", "c0030"), ("B_05.01", "c0010", "c0050", "c0080")),
)


class ReportingEntityListedRule:
    """REL-001: B_01.02 lists the entity of B_01.01 (ITS, annex I, B_01.02)."""

    id = "REL-001"
    codes = ("REL-001",)

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        if "B_01.02" not in dataset.tables:
            return []
        group = by_code(dataset, "B_01.02", "c0010")
        missing = [
            r for r in rows(dataset, "B_01.01", "c0010") if r["c0010"] and r["c0010"] not in group
        ]
        if not missing:
            return []
        places = [
            Occurrence(
                table="B_01.01",
                row=r[ROW_COLUMN],
                column="c0010",
                value=r["c0010"],
                target_table="B_01.02",
                target_column="c0010",
                side="source",
            )
            for r in missing
        ]
        lines = [f"#{r[ROW_COLUMN]} · {r['c0010']!r}" for r in missing]
        return [_finding(self.id, "B_01.01", places, lines)]


class SameEntityAttributesRule:
    """REL-002, REL-003, REL-004: name and country of a LEI identical across tables."""

    id = "REL-002"
    codes = ("REL-002", "REL-003", "REL-004")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        found: list[ValidationMessage] = []
        for (s_table, s_key, s_name, s_country), (t_table, t_key, t_name, t_country) in PAIRS:
            targets = by_code(dataset, t_table, t_key, t_name, t_country)
            conflicts: dict[str, tuple[list[Occurrence], list[str]]] = {
                "REL-002": ([], []),
                "REL-003": ([], []),
                "REL-004": ([], []),
            }
            for source in rows(dataset, s_table, s_key, s_name, s_country):
                target = targets.get(source[s_key]) if source[s_key] else None
                if target is None:
                    continue
                name, other = source[s_name], target[t_name]
                if name and other and name != other:
                    code = "REL-002" if normalise_name(name) != normalise_name(other) else "REL-003"
                    places, line = _pair((s_table, source, s_name), (t_table, target, t_name))
                    conflicts[code][0].extend(places)
                    conflicts[code][1].append(line)
                if (
                    source[s_country]
                    and target[t_country]
                    and source[s_country] != target[t_country]
                ):
                    places, line = _pair((s_table, source, s_country), (t_table, target, t_country))
                    conflicts["REL-004"][0].extend(places)
                    conflicts["REL-004"][1].append(line)
            for code, (places, lines) in conflicts.items():
                if lines:
                    found.append(_finding(code, s_table, places, lines, target=t_table))
        return found


def _parents(group: dict[str, dict]) -> dict[str, str | None]:
    return {lei: row["c0060"] for lei, row in group.items()}


def _chain(lei: str, parents: dict[str, str | None]) -> tuple[list[str], bool]:
    """Entities from ``lei`` up its direct parents; True when a cycle was met."""
    chain = [lei]
    current = lei
    while True:
        parent = parents.get(current)
        if parent is None or parent == current or parent not in parents:
            return chain, False
        if parent in chain:
            return chain, True
        chain.append(parent)
        current = parent


class GroupUltimateParentRule:
    """BUS-001 and BUS-002: one ultimate parent, reached by every chain of direct parents."""

    id = "BUS-001"
    codes = ("BUS-001", "BUS-002")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        group = by_code(dataset, "B_01.02", "c0010", "c0050", "c0060")
        if not group:
            return []
        found: list[ValidationMessage] = []
        tops = [row for row in group.values() if row["c0050"] == ULTIMATE_PARENT]
        if len(tops) > 1:
            places = [
                Occurrence(table="B_01.02", row=r[ROW_COLUMN], column="c0050", value=r["c0050"])
                for r in tops
            ]
            lines = [f"#{r[ROW_COLUMN]} · {r['c0010']!r}" for r in tops]
            found.append(_finding("BUS-001", "B_01.02", places, lines))

        top_leis = {r["c0010"] for r in tops}
        parents = _parents(group)
        broken: list[dict] = []
        for lei, row in group.items():
            if row["c0060"] is None:
                continue  # empty parent: a mandatory value, reported by the EBA rules
            chain, cycle = _chain(lei, parents)
            if row["c0060"] not in parents:
                continue  # unknown parent: DAT-005 (R6)
            if cycle or chain[-1] not in top_leis:
                broken.append(row)
        if broken and top_leis:
            places = [
                Occurrence(table="B_01.02", row=r[ROW_COLUMN], column="c0060", value=r["c0060"])
                for r in broken
            ]
            lines = [f"#{r[ROW_COLUMN]} · {r['c0010']!r} → {r['c0060']!r}" for r in broken]
            found.append(_finding("BUS-002", "B_01.02", places, lines))
        return found


class ProviderUltimateParentRule:
    """REL-005, BUS-003, BUS-004: ultimate parents of the ICT providers (B_05.01.0110, 0120)."""

    id = "BUS-003"
    codes = ("BUS-003", "BUS-004", "REL-005")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        providers = by_code(dataset, "B_05.01", "c0010", "c0020", "c0110", "c0120")
        if not providers:
            return []
        found: list[ValidationMessage] = []
        type_places, type_lines, own_places, own_lines = [], [], [], []
        for row in providers.values():
            parent = providers.get(row["c0110"]) if row["c0110"] else None
            if parent is None:
                continue  # empty: EBA rules; unknown: DAT-005 (R18)
            if row["c0120"] and parent["c0020"] and row["c0120"] != parent["c0020"]:
                places, line = _pair(("B_05.01", row, "c0120"), ("B_05.01", parent, "c0020"))
                type_places += places
                type_lines.append(line)
            if parent["c0110"] and parent["c0110"] != parent["c0010"] and parent is not row:
                own_places.append(
                    Occurrence(
                        table="B_05.01",
                        row=parent[ROW_COLUMN],
                        column="c0110",
                        value=parent["c0110"],
                    )
                )
                own_lines.append(
                    f"#{parent[ROW_COLUMN]} · {parent['c0010']!r} → {parent['c0110']!r}"
                )
        if type_lines:
            found.append(_finding("BUS-003", "B_05.01", type_places, type_lines))
        if own_lines:
            unique = _unique(zip(own_places, own_lines, strict=True))
            found.append(
                _finding("BUS-004", "B_05.01", [p for p, _ in unique], [li for _, li in unique])
            )
        found += self._intra_group(dataset, providers)
        return found

    @staticmethod
    def _intra_group(dataset: RoIDataset, providers: dict[str, dict]) -> list[ValidationMessage]:
        """REL-005: an intra-group provider names a parent from its own chain (PO, 29/10)."""
        group = by_code(dataset, "B_01.02", "c0010", "c0040", "c0060")
        parents = _parents(group)
        places, lines = [], []
        for lei, entity in group.items():
            provider = providers.get(lei)
            if entity["c0040"] != INTRA_GROUP_PROVIDER or provider is None:
                continue
            ultimate = provider["c0110"]
            if not ultimate or ultimate not in providers:
                continue
            chain, _ = _chain(lei, parents)
            if ultimate not in chain[1:]:
                pair, line = _pair(("B_05.01", provider, "c0110"), ("B_01.02", entity, "c0060"))
                places += pair
                lines.append(line)
        if not lines:
            return []
        return [_finding("REL-005", "B_05.01", places, lines, target="B_01.02")]


def _unique(items: Iterable[tuple[Occurrence, str]]) -> list[tuple[Occurrence, str]]:
    seen: set[int | None] = set()
    kept = []
    for place, line in items:
        if place.row not in seen:
            seen.add(place.row)
            kept.append((place, line))
    return kept


class EntityDatesRule:
    """BUS-005: B_01.02, integration (0080) <= last update (0070) <= ... and deletion (0090)."""

    id = "BUS-005"
    codes = ("BUS-005",)

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        places, lines = [], []
        for row in rows(dataset, "B_01.02", "c0010", "c0070", "c0080", "c0090"):
            update, integration, deletion = row["c0070"], row["c0080"], row["c0090"]
            wrong = []
            if integration and update and integration > update:
                wrong.append("c0080")
            if integration and deletion and deletion != OPEN_DATE and deletion < integration:
                wrong.append("c0090")
            for column in wrong:
                places.append(
                    Occurrence(
                        table="B_01.02", row=row[ROW_COLUMN], column=column, value=row[column]
                    )
                )
            if wrong:
                lines.append(
                    f"#{row[ROW_COLUMN]} · {row['c0010']!r} : 0070={update} 0080={integration} "
                    f"0090={deletion}"
                )
        if not lines:
            return []
        return [_finding(self.id, "B_01.02", places, lines)]


def entity_rules() -> list:
    return [
        ReportingEntityListedRule(),
        SameEntityAttributesRule(),
        GroupUltimateParentRule(),
        ProviderUltimateParentRule(),
        EntityDatesRule(),
    ]
