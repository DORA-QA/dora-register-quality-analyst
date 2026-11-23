# SPDX-License-Identifier: EUPL-1.2
"""Sprint 3, lot 2: ICT third-party service providers (brief §6, §12; additions of 29/10).

REL-006  type of code repeated in another table different from B_05.01.0020 (BLOCKER, provisional)
REL-007  provider, legal person, identified by neither a LEI nor an EUID (ITS art. 3 §5);
         every provider of B_05.01 since 0.8.1, not only the direct ones (decision of the PO, 02/11)
DQ-001   probable duplicate: same normalised name and same country, different codes
DQ-002   probable duplicate: additional code of a provider = main code of another provider
DQ-003   probable duplicate: French EUID whose SIREN is the main code of another provider
DQ-004   provider listed in B_05.01 but used nowhere (ultimate parents excepted)

Codes are compared exactly. Names are compared after normalisation, legal forms removed,
the name in Latin alphabet (B_05.01.0060) first. Nothing is merged or corrected.
"""

import re

from contracts import identifiers
from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from contracts.naming import field_reference
from rules.business.common import ROW_COLUMN, by_code, normalise_name, rows
from rules.technical.locations import describe

LEI_TYPE = "eba_qCO:qx2000"
EUID_TYPE = "eba_qCO:qx2002"
LEGAL_PERSON = "eba_CT:x212"

# Columns repeating a provider's code, with the column of its type (brief §6.2).
REPEATED_TYPES = (
    ("B_02.02", "c0030", "c0040"),
    ("B_03.02", "c0020", "c0030"),
    ("B_05.02", "c0030", "c0040"),
    ("B_05.02", "c0060", "c0070"),
    ("B_07.01", "c0020", "c0030"),
)
# Columns where a provider is used (brief §6.5); B_05.01.0110 of another provider is handled apart.
USES = (
    ("B_02.02", "c0030"),
    ("B_03.02", "c0020"),
    ("B_05.02", "c0030"),
    ("B_05.02", "c0060"),
    ("B_07.01", "c0020"),
)
# Usual legal forms, removed from names before looking for duplicates (brief §6.4).
LEGAL_FORMS = frozenset(
    {
        "sa",
        "sas",
        "sasu",
        "sarl",
        "eurl",
        "sca",
        "scs",
        "snc",
        "se",
        "sci",
        "gie",
        "selarl",
        "gmbh",
        "ag",
        "kg",
        "ohg",
        "ug",
        "ltd",
        "limited",
        "llc",
        "llp",
        "lp",
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "plc",
        "bv",
        "nv",
        "spa",
        "srl",
        "sl",
        "oy",
        "ab",
        "as",
        "aps",
        "asa",
        "sp",
        "zoo",
        "kft",
        "sro",
    }
)
_DOTS = re.compile(r"\.")


def company_key(name: str) -> str:
    """Name for duplicate detection: 'Microsoft France S.A.S.' -> 'microsoft france'."""
    tokens = normalise_name(_DOTS.sub("", name)).split()
    return " ".join(token for token in tokens if token not in LEGAL_FORMS)


def siren_of(code: str) -> str | None:
    """SIREN carried by a French identifier: SIREN, SIRET, VAT (FR + key + SIREN) or EUID."""
    text = code.strip().upper()
    if identifiers.SIREN.match(text):
        return text
    if identifiers.SIRET.match(text):
        return text[:9]
    if identifiers.FRENCH_VAT.match(text) or identifiers.FRENCH_EUID.match(text):
        return text[-9:]
    return None


def _finding(code: str, table: str, places: list[Occurrence], lines: list[str], **params):
    message = make_message(code, details=describe(lines), table=table, count=len(lines), **params)
    return with_occurrences(message, places)


def _providers(dataset: RoIDataset) -> dict[str, dict]:
    return by_code(
        dataset,
        "B_05.01",
        "c0010",
        "c0020",
        "c0030",
        "c0040",
        "c0050",
        "c0060",
        "c0070",
        "c0080",
        "c0110",
    )


class RepeatedTypeOfCodeRule:
    """REL-006: a provider's type of code is the one of B_05.01.0020 wherever it is repeated."""

    id = "REL-006"
    codes = ("REL-006",)

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        providers = _providers(dataset)
        if not providers:
            return []
        found: list[ValidationMessage] = []
        by_table: dict[str, tuple[list[Occurrence], list[str]]] = {}
        for table, code_column, type_column in REPEATED_TYPES:
            for row in rows(dataset, table, code_column, type_column):
                provider = providers.get(row[code_column]) if row[code_column] else None
                if provider is None or not row[type_column] or not provider["c0020"]:
                    continue  # unknown code: DAT-005; empty type: mandatory rules
                if row[type_column] == provider["c0020"]:
                    continue
                places, lines = by_table.setdefault(table, ([], []))
                places += [
                    Occurrence(
                        table=table,
                        row=row[ROW_COLUMN],
                        column=type_column,
                        value=row[type_column],
                        target_table="B_05.01",
                        target_column="c0020",
                        side="source",
                    ),
                    Occurrence(
                        table="B_05.01",
                        row=provider[ROW_COLUMN],
                        column="c0020",
                        value=provider["c0020"],
                        side="target",
                    ),
                ]
                lines.append(
                    f"#{row[ROW_COLUMN]} · {field_reference(table, type_column)} "
                    f"{row[type_column]!r} ≠ B_05.01.0020 {provider['c0020']!r} "
                    f"({row[code_column]!r})"
                )
        for table, (places, lines) in by_table.items():
            found.append(_finding(self.id, table, places, lines))
        return found


class ProviderIdentifierRule:
    """REL-007: ITS art. 3 §5, a provider that is a legal person has a LEI or an EUID.

    Every legal person of B_05.01 is checked: direct providers, subcontractors and ultimate
    parents (decision of the PO, 02/11/2026; until 0.8.0, direct providers only).
    """

    id = "REL-007"
    codes = ("REL-007",)

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        providers = _providers(dataset)
        places, lines = [], []
        for code in sorted(providers):
            provider = providers[code]
            if provider["c0070"] != LEGAL_PERSON or not provider["c0020"]:
                continue
            if provider["c0020"] in (LEI_TYPE, EUID_TYPE):
                continue
            places.append(
                Occurrence(
                    table="B_05.01",
                    row=provider[ROW_COLUMN],
                    column="c0020",
                    value=provider["c0020"],
                    # The type of person (legal person) is what requires a LEI or an EUID (E13).
                    target_table="B_05.01",
                    target_column="c0070",
                    side="source",
                )
            )
            lines.append(f"#{provider[ROW_COLUMN]} · {code!r} : {provider['c0020']}")
        if not lines:
            return []
        return [_finding(self.id, "B_05.01", places, lines)]


class ProbableDuplicateProviderRule:
    """DQ-001, DQ-002, DQ-003: one provider probably reported twice (expert advice, no merge)."""

    id = "DQ-001"
    codes = ("DQ-001", "DQ-002", "DQ-003")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        providers = _providers(dataset)
        if len(providers) < 2:
            return []
        return [
            *self._same_name(providers),
            *self._additional_code(providers),
            *self._siren(providers),
        ]

    @staticmethod
    def _same_name(providers: dict[str, dict]) -> list[ValidationMessage]:
        groups: dict[tuple[str, str], list[dict]] = {}
        for row in providers.values():
            name = row["c0060"] or row["c0050"]
            if not name or not row["c0080"]:
                continue
            key = company_key(name)
            if key:
                groups.setdefault((key, row["c0080"]), []).append(row)
        places, lines = [], []
        for members in groups.values():
            if len(members) < 2:
                continue
            for row in members:
                places.append(
                    Occurrence(
                        table="B_05.01", row=row[ROW_COLUMN], column="c0010", value=row["c0010"]
                    )
                )
            names = ", ".join(f"#{r[ROW_COLUMN]} {r['c0050']!r} ({r['c0010']})" for r in members)
            lines.append(names)
        if not lines:
            return []
        return [_finding("DQ-001", "B_05.01", places, lines)]

    @staticmethod
    def _additional_code(providers: dict[str, dict]) -> list[ValidationMessage]:
        places, lines = [], []
        for row in providers.values():
            other = providers.get(row["c0030"]) if row["c0030"] else None
            if other is None or other is row:
                continue
            places += [
                Occurrence(
                    table="B_05.01",
                    row=row[ROW_COLUMN],
                    column="c0030",
                    value=row["c0030"],
                    target_table="B_05.01",
                    target_column="c0010",
                    side="source",
                ),
                Occurrence(
                    table="B_05.01",
                    row=other[ROW_COLUMN],
                    column="c0010",
                    value=other["c0010"],
                    side="target",
                ),
            ]
            lines.append(
                f"#{row[ROW_COLUMN]} · B_05.01.0030 {row['c0030']!r} = B_05.01.0010 "
                f"(#{other[ROW_COLUMN]})"
            )
        if not lines:
            return []
        return [_finding("DQ-002", "B_05.01", places, lines)]

    @staticmethod
    def _siren(providers: dict[str, dict]) -> list[ValidationMessage]:
        main_sirens: dict[str, dict] = {}
        for row in providers.values():
            if row["c0020"] != EUID_TYPE:
                siren = siren_of(row["c0010"])
                if siren:
                    main_sirens.setdefault(siren, row)
        places, lines = [], []
        for row in providers.values():
            if row["c0020"] != EUID_TYPE or not identifiers.FRENCH_EUID.match(row["c0010"]):
                continue
            other = main_sirens.get(row["c0010"][-9:])
            if other is None or other is row:
                continue
            places += [
                Occurrence(
                    table="B_05.01",
                    row=row[ROW_COLUMN],
                    column="c0010",
                    value=row["c0010"],
                    target_table="B_05.01",
                    target_column="c0010",
                    side="source",
                ),
                Occurrence(
                    table="B_05.01",
                    row=other[ROW_COLUMN],
                    column="c0010",
                    value=other["c0010"],
                    side="target",
                ),
            ]
            lines.append(
                f"#{row[ROW_COLUMN]} · {row['c0010']!r} ~ {other['c0010']!r} (#{other[ROW_COLUMN]})"
            )
        if not lines:
            return []
        return [_finding("DQ-003", "B_05.01", places, lines)]


class UnusedProviderRule:
    """DQ-004: a provider of B_05.01 that no arrangement, chain or assessment uses (INFO)."""

    id = "DQ-004"
    codes = ("DQ-004",)

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        providers = _providers(dataset)
        if not providers:
            return []
        used = {r[c] for table, c in USES for r in rows(dataset, table, c) if r[c]}
        # Ultimate parents are listed by the ITS without being used (brief §6.5).
        used |= {r["c0110"] for r in providers.values() if r["c0110"] and r["c0110"] != r["c0010"]}
        unused = [r for code, r in providers.items() if code not in used]
        if not unused:
            return []
        places = [
            Occurrence(table="B_05.01", row=r[ROW_COLUMN], column="c0010", value=r["c0010"])
            for r in unused
        ]
        lines = [
            f"#{r[ROW_COLUMN]} · {r['c0010']!r}" + (f" {r['c0050']!r}" if r["c0050"] else "")
            for r in unused
        ]
        return [_finding(self.id, "B_05.01", places, lines)]


def provider_rules() -> list:
    return [
        RepeatedTypeOfCodeRule(),
        ProviderIdentifierRule(),
        ProbableDuplicateProviderRule(),
        UnusedProviderRule(),
    ]
