# SPDX-License-Identifier: EUPL-1.2
"""LEI against the local copy of the GLEIF data (branch feature/gleif-local).

GLF-001  LEI absent from GLEIF: EBA rules VR_2, VR_12, VR_23, VR_71, VR_77 (warning, no reject)
GLF-002  LEI not valid (RETIRED, MERGED, ANNULLED, DUPLICATE, PENDING_*) or entity INACTIVE
         (ITS art. 3 §5; PO decision of 08/11/2026 for DUPLICATE, ANNULLED and PENDING_*)
GLF-003  LEI not renewed (LAPSED): "valid and active" LEI required (ITS art. 3 §5); the ESAs did
         not enforce the status in 2025 (EBA FAQ Q44)
GLF-004  renewal due before the probable end of the EBA processing (30 April after the
         reference date)
GLF-005  country of B_01.02.0030 different from GLEIF: EBA rule VR_16
GLF-006  country of B_01.01.0030 or B_05.01.0080 different from GLEIF
GLF-007  name different from the GLEIF legal name
GLF-008  direct parent (B_01.02.0060) different from the GLEIF direct parent
GLF-009  ultimate parent (B_05.01.0110) of a provider identified by LEI different from the GLEIF
         ultimate parent (empty, or identified otherwise than by LEI, counts as different)
GLF-010  no GLEIF copy installed: the checks above are "not evaluated"
GLF-011  GLEIF copy older than ``STALE_DAYS`` days

Only well-formed LEI are looked up (the format is DAT-006 to DAT-010's business). Countries are
compared with the legal address and the headquarters of the GLEIF record (either one matches):
the EBA does not say which one VR_16 uses. The status is the status of the copy installed, whose
date is quoted in every finding; the EBA checks against its own cache when it processes the
register (see docs/gleif.md).
"""

from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from difflib import SequenceMatcher

from contracts import identifiers
from contracts.dataset import RoIDataset
from contracts.gleif import (
    ACTIVE_ENTITY,
    DIRECT_PARENT,
    ISSUED,
    LAPSED,
    NOT_VALID,
    ULTIMATE_PARENT,
    GleifCoverage,
    GleifRecord,
    GleifSnapshot,
    IGleifLookup,
)
from contracts.messages import ValidationMessage, make_message
from contracts.naming import field_reference
from contracts.tables import ROW_COLUMN, rows
from rules.business.common import normalise_name
from rules.technical.locations import Hit, describe, hit, located

LEI_TYPE = "eba_qCO:qx2000"
STALE_DAYS = 7
NAME_SIMILARITY = 0.85

# (EBA rule, table, LEI column, type column or None, name columns, country column)
LEI_FIELDS: tuple[tuple[str, str, str, str | None, tuple[str, ...], str | None], ...] = (
    ("VR_2", "B_01.01", "c0010", None, ("c0020",), "c0030"),
    ("VR_12", "B_01.02", "c0010", None, ("c0020",), "c0030"),
    ("VR_23", "B_01.02", "c0060", None, (), None),
    ("VR_71", "B_05.01", "c0010", "c0020", ("c0050", "c0060"), "c0080"),
    ("VR_77", "B_05.01", "c0030", "c0040", (), None),
)
CODES = tuple(f"GLF-{n:03d}" for n in range(1, 12))
EVALUATED_CODES = CODES[:9]


class Cell:
    __slots__ = ("rule", "table", "column", "row", "lei", "names", "country", "values")

    def __init__(self, rule: str, table: str, column: str, row: int, lei: str) -> None:
        self.rule, self.table, self.column, self.row, self.lei = rule, table, column, row, lei
        self.names: tuple[str, ...] = ()
        self.country: tuple[str, str] | None = None  # (column, declared country)
        self.values: dict[str, str | None] = {}


# add(code, cell, column, value shown, suffix of the line)
Add = Callable[[str, "Cell", str, str, str], None]


def _cells(dataset: RoIDataset) -> Iterator[Cell]:
    for rule, table, column, type_column, names, country in LEI_FIELDS:
        wanted = [column, *names]
        if type_column:
            wanted.append(type_column)
        if country:
            wanted.append(country)
        if table == "B_01.02":
            wanted.append("c0060")
        if table == "B_05.01":
            wanted += ["c0110", "c0120"]
        frame = dataset.tables.get(table)
        if frame is None:
            continue
        present = [c for c in dict.fromkeys(wanted) if c in frame.columns]
        for row in rows(dataset, table, *present):
            value = row.get(column)
            if not value or (type_column and row.get(type_column) != LEI_TYPE):
                continue
            lei = str(value).strip()
            if identifiers.analyse_lei(lei).problem != identifiers.LEI_OK:
                continue
            cell = Cell(rule, table, column, int(str(row[ROW_COLUMN])), lei)
            cell.names = tuple(str(row[n]) for n in names if row.get(n))
            if country and row.get(country):
                cell.country = (country, str(row[country]).rsplit(":", 1)[-1])
            cell.values = {k: (None if v is None else str(v)) for k, v in row.items()}
            yield cell


def looked_up(dataset: RoIDataset) -> set[str]:
    """Distinct well-formed LEI the rule looks up (for the summary of the report)."""
    return {cell.lei for cell in _cells(dataset)}


def coverage(
    dataset: RoIDataset, messages: list[ValidationMessage], snapshot: GleifSnapshot | None
) -> GleifCoverage:
    """What the summary of the report says: LEI checked and distinct LEI by kind of problem."""
    if snapshot is None:
        return GleifCoverage(available=False, checked=len(looked_up(dataset)), copy_date=None)
    distinct: dict[str, set[str]] = {code: set() for code in CODES[:4]}
    mismatches = 0
    for message in messages:
        if message.code in distinct:
            distinct[message.code].update(o.value for o in message.occurrences if o.value)
        elif message.code in CODES[4:9]:
            mismatches += len(message.occurrences)
    return GleifCoverage(
        available=True,
        checked=len(looked_up(dataset)),
        copy_date=snapshot.content_date[:10],
        absent=len(distinct["GLF-001"]),
        invalid=len(distinct["GLF-002"]),
        lapsed=len(distinct["GLF-003"]),
        due=len(distinct["GLF-004"]),
        mismatches=mismatches,
    )


def _similar(declared: str, legal: str) -> bool:
    a, b = normalise_name(declared), normalise_name(legal)
    if not a or not b:
        return True
    if a == b or a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= NAME_SIMILARITY


def _deadline(dataset: RoIDataset) -> str | None:
    """30 April of the year after the reference date (yyyy-mm-dd), or None."""
    reference = dataset.package_metadata.reference_date or ""
    try:
        year = date.fromisoformat(reference[:10]).year
    except ValueError:
        return None
    return f"{year + 1}-04-30"


class GleifRule:
    id = "GLEIF"
    codes = CODES

    def __init__(self, lookup: IGleifLookup | None, today: date | None = None) -> None:
        self._lookup = lookup
        self._today = today
        # Codes that could not be evaluated during the last run (no copy installed).
        self.skipped_codes: tuple[str, ...] = ()

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        snapshot = self._lookup.snapshot if self._lookup is not None else None
        if self._lookup is None or snapshot is None:
            self.skipped_codes = EVALUATED_CODES
            return [make_message("GLF-010")]
        self.skipped_codes = ()
        lookup = self._lookup
        copy_date = snapshot.content_date[:10]
        cells = list(_cells(dataset))
        found: dict[str, dict[tuple[str, str], list[Hit]]] = {}
        rule_of: dict[tuple[str, str], str] = {}

        def add(code: str, cell: Cell, column: str, value: str, suffix: str = "") -> None:
            place = (cell.table, column)
            found.setdefault(code, {}).setdefault(place, []).append(hit(cell.row, value, suffix))
            rule_of.setdefault(place, cell.rule)

        records = lookup.records({c.lei for c in cells}) if cells else {}
        deadline = _deadline(dataset)
        for cell in cells:
            record = records.get(cell.lei)
            if record is None:
                add("GLF-001", cell, cell.column, cell.lei, "")
                continue
            self._status(cell, record, deadline, add)
            self._country(cell, record, add)
            self._name(cell, record, add)
        self._parents(cells, records, add)

        messages: list[ValidationMessage] = []
        stale = self._stale(snapshot.content_date)
        if stale is not None:
            messages.append(make_message("GLF-011", copy_date=copy_date, days=stale))
        for code in CODES:
            for (table, column), hits in sorted(found.get(code, {}).items()):
                message = make_message(
                    code,
                    details=describe([h.text for h in hits]),
                    table=table,
                    column=field_reference(table, column),
                    count=len(hits),
                    rule=rule_of[(table, column)],
                    copy_date=copy_date,
                    deadline=deadline or "",
                )
                messages.append(located(message, table, column, hits))
        return messages

    @staticmethod
    def _status(cell: Cell, record: GleifRecord, deadline: str | None, add: Add) -> None:
        status = record.registration_status or ""
        if status in NOT_VALID or record.entity_status not in (None, ACTIVE_ENTITY):
            label = status if status in NOT_VALID else f"{status}, {record.entity_status}"
            successor = f" → {record.successor_lei}" if record.successor_lei else ""
            add("GLF-002", cell, cell.column, cell.lei, f" ({label}){successor}")
        elif status == LAPSED:
            renewal = f", {record.next_renewal}" if record.next_renewal else ""
            add("GLF-003", cell, cell.column, cell.lei, f" (LAPSED{renewal})")
        elif (
            status == ISSUED and deadline and record.next_renewal and record.next_renewal < deadline
        ):
            add("GLF-004", cell, cell.column, cell.lei, f" ({record.next_renewal})")

    @staticmethod
    def _country(cell: Cell, record: GleifRecord, add: Add) -> None:
        if cell.country is None:
            return
        column, declared = cell.country
        known = {c for c in (record.legal_country, record.hq_country) if c}
        if known and not any(identifiers.same_country(declared, c) for c in known):
            code = "GLF-005" if cell.table == "B_01.02" else "GLF-006"
            add(code, cell, column, declared, f" ≠ GLEIF {'/'.join(sorted(known))} ({cell.lei})")

    @staticmethod
    def _name(cell: Cell, record: GleifRecord, add: Add) -> None:
        if not cell.names or not record.legal_name:
            return
        if not any(_similar(name, record.legal_name) for name in cell.names):
            add(
                "GLF-007",
                cell,
                cell.column,
                cell.names[0],
                f" ≠ GLEIF {record.legal_name!r} ({cell.lei})",
            )

    def _parents(self, cells: list[Cell], records: dict[str, GleifRecord], add: Add) -> None:
        assert self._lookup is not None
        entities = [c for c in cells if c.table == "B_01.02" and c.column == "c0010"]
        providers = [c for c in cells if c.table == "B_05.01" and c.column == "c0010"]
        direct = self._lookup.parents({c.lei for c in entities if c.lei in records}, DIRECT_PARENT)
        ultimate = self._lookup.parents(
            {c.lei for c in providers if c.lei in records}, ULTIMATE_PARENT
        )
        for cell in entities:
            declared = (cell.values.get("c0060") or "").strip()
            expected = direct.get(cell.lei)
            if declared and expected and declared not in (expected, cell.lei):
                add("GLF-008", cell, "c0060", declared, f" ≠ GLEIF {expected} ({cell.lei})")
        for cell in providers:
            # PO decision of 08/11/2026: for every provider identified by LEI, the ultimate parent
            # reported in 0110 must be the one recorded in GLEIF. Not checked when GLEIF records no
            # ultimate parent (the level 2 exceptions are not used).
            expected = ultimate.get(cell.lei)
            if expected is None:
                continue
            declared = (cell.values.get("c0110") or "").strip()
            typed_lei = cell.values.get("c0120") == LEI_TYPE
            if declared == expected and typed_lei:
                continue
            shown = declared or "∅"
            if declared and not typed_lei:
                shown += f" [{(cell.values.get('c0120') or '').rsplit(':', 1)[-1] or '?'}]"
            add("GLF-009", cell, "c0110", shown, f" ≠ GLEIF {expected} ({cell.lei})")

    def _stale(self, content_date: str) -> int | None:
        try:
            published = datetime.fromisoformat(content_date.replace("Z", "+00:00")).date()
        except ValueError:
            return None
        today = self._today or datetime.now(UTC).date()
        age = (today - published).days
        return age if age > STALE_DAYS else None
