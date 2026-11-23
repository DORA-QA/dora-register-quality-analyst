# SPDX-License-Identifier: EUPL-1.2
"""Checks performed on a file.

The registry (``reference/checks/checks.json``) has one entry per finding code
(source, version of introduction, severity status); the ``group`` field gathers
the codes into the checks shown to the reader. A check groups one or more codes: it fails
when one of them is a blocker, warns when only lighter findings are present, and passes when
its step ran without any of its codes. A check whose step did not run is skipped: it is
left out of the counts but, when it concerns the file, it earns nothing in the score, so a file
that stops early cannot look good because little was checked.

Each check carries a weight, the seriousness of its most serious code. The scores built on these
weights are computed by the ``scoring`` module (formula in ``docs/scores.md``), not here.
"""

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from contracts.json_types import JsonDict
from contracts.messages import CATALOG_DIR, CATALOG_FILE, Severity, ValidationMessage, load_catalog

# Origin of a rule (CL-30, Sprint 3 question 72): an attribute that may evolve, not a category.
ORIGINS = frozenset({"OFFICIAL", "PO_VALIDATED", "TECHNICAL", "DATA_QUALITY"})
# Validation cycle: PROVISIONAL -> PO_VALIDATED -> CONFIRMED (read as AUTHORITY_CONFIRMED).
SEVERITY_STATUSES = frozenset({"CONFIRMED", "PROVISIONAL", "PO_VALIDATED"})
CHECKS_FILE = Path(__file__).resolve().parent.parent / "reference" / "checks" / "checks.json"
SEVERITY_WEIGHT = {Severity.BLOCKER: 5, Severity.MAJOR: 3, Severity.MINOR: 1, Severity.INFO: 1}
XML_SOURCE = "XML"


class CheckStatus(StrEnum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    # The check ran, but a column it reads is missing from the file (red team RT-09): finding
    # nothing then proves nothing, so the check is neither passed nor scored.
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class CheckDefinition:
    id: str
    category: str
    step: str
    codes: tuple[str, ...]
    xml_only: bool
    weight: int
    origins: tuple[str, ...] = ()
    source_tables: tuple[str, ...] = ()
    target_tables: tuple[str, ...] = ()
    # False: the check is shown but has no effect on the scores (weight 0), as decided by the
    # PO for the consistency of the amounts (PO-35, CL-44).
    scored: bool = True


@dataclass(frozen=True)
class CheckResult:
    definition: CheckDefinition
    status: CheckStatus
    codes_found: tuple[str, ...]
    # False when the check does not concern this kind of file (envelope checks on a ZIP).
    applicable: bool = True


@lru_cache
def load_registry() -> tuple[JsonDict, ...]:
    """The registry as written in the file: one entry per finding code."""
    return tuple(json.loads(CHECKS_FILE.read_text(encoding="utf-8"))["checks"])


@lru_cache
def catalog_fingerprint() -> str:
    """First 12 characters of the SHA-256 of the registry and the catalogue of messages.

    Two analyses with the same fingerprint ran the same checks, with the same severities.
    """
    digest = hashlib.sha256()
    for path in (CHECKS_FILE, CATALOG_DIR / CATALOG_FILE):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


@lru_cache
def load_checks() -> tuple[CheckDefinition, ...]:
    catalog = load_catalog()
    groups: dict[str, list[JsonDict]] = {}
    for entry in load_registry():
        groups.setdefault(entry["group"], []).append(entry)
    return tuple(
        CheckDefinition(
            id=group,
            category=entries[0]["category"],
            step=entries[0]["step"],
            codes=tuple(e["code"] for e in entries),
            xml_only=entries[0]["xml_only"],
            weight=(
                max(SEVERITY_WEIGHT[Severity(catalog[e["code"]]["severity"])] for e in entries)
                if all(e.get("scored", True) for e in entries)
                else 0
            ),
            scored=all(e.get("scored", True) for e in entries),
            origins=_distinct(e["origin"] for e in entries),
            source_tables=_distinct(t for e in entries for t in e.get("source_tables", ())),
            target_tables=_distinct(t for e in entries for t in e.get("target_tables", ())),
        )
        for group, entries in groups.items()
    )


def _distinct(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def origin_of_code(code: str) -> str | None:
    """OFFICIAL, PO_VALIDATED, TECHNICAL or DATA_QUALITY, as written in the registry."""
    for entry in load_registry():
        if entry["code"] == code:
            return str(entry["origin"])
    return None


def check_of_code(code: str) -> str | None:
    for definition in load_checks():
        if code in definition.codes:
            return definition.id
    return None


def category_of_code(code: str) -> str | None:
    for definition in load_checks():
        if code in definition.codes:
            return definition.category
    return None


def evaluate_checks(
    messages: Iterable[ValidationMessage],
    steps: Mapping[str, str],
    source_type: str,
    blind_codes: Iterable[str] = (),
) -> list[CheckResult]:
    by_code: dict[str, list[Severity]] = {}
    for message in messages:
        by_code.setdefault(message.code, []).append(message.severity)

    blind = set(blind_codes)
    results = []
    for definition in load_checks():
        concerns_file = not definition.xml_only or source_type == XML_SOURCE
        applicable = concerns_file and steps.get(definition.step, "SKIPPED") != "SKIPPED"
        found = [code for code in definition.codes if code in by_code]
        if not applicable and not found:
            status = CheckStatus.SKIPPED
        elif any(Severity.BLOCKER in by_code[code] for code in found):
            status = CheckStatus.FAILED
        elif found:
            status = CheckStatus.WARNING
        elif blind & set(definition.codes):
            status = CheckStatus.NOT_EVALUATED
        else:
            status = CheckStatus.PASSED
        results.append(CheckResult(definition, status, tuple(found), concerns_file))
    return results
