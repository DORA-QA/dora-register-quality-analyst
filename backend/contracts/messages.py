# SPDX-License-Identifier: EUPL-1.2
"""Validation messages shared by every engine.

A finding is stored without any text: a code, its parameters and technical
details. The texts (statement, explanation, action, expert advice, source) are
produced only when the finding is displayed, in the language requested. The same
finding can therefore be shown in several languages without running the
controls again.

Data files, in ``reference/messages``:

- ``catalog.json``: what does not depend on the language (severity, type of
  source, codes used by the authorities);
- ``<language>.json``: the texts of one language.
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import cast

from contracts import data_model
from contracts.json_types import JsonDict

CATALOG_DIR = Path(__file__).resolve().parent.parent / "reference" / "messages"
CATALOG_FILE = "catalog.json"
DEFAULT_LANGUAGE = "en"
TEXT_FIELDS = ("message", "explanation", "recommendation", "expert_advice")


class Severity(StrEnum):
    """Severity levels, from the most to the least serious."""

    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


class ReferenceType(StrEnum):
    """Where a control comes from, so the reader knows what it is worth."""

    REGULATORY = "regulatory"  # regulation or filing rule
    OFFICIAL_GUIDE = "official_guide"  # guidance published by an authority
    PRODUCT = "product"  # technical check of this product, no regulatory source


@dataclass(frozen=True)
class Fragment:
    """A piece of text chosen by the code and written in the language files.

    Used wherever an engine would otherwise write words: a reason, an expected
    format, a located detail.
    """

    key: str
    params: Mapping[str, object] = field(default_factory=dict)


def fragment(key: str, **params: object) -> Fragment:
    return Fragment(key, params)


@dataclass(frozen=True)
class Label:
    """A field or a list member, written with its official label in the language asked.

    ``kind`` is "field" (``B_07.01.0050``) or "member" (``eba_ZZ:x959``). The code stays
    visible next to the label of a field, so that the user can find the column (PO, #179).
    """

    kind: str
    code: str


def field_label(code: str) -> Label:
    return Label("field", code)


def member_label(code: str) -> Label:
    return Label("member", code)


def table_label(code: str) -> Label:
    return Label("table", code)


@dataclass(frozen=True)
class Joined:
    """Several pieces written one after the other, the last two linked by "or" or "and"."""

    parts: tuple[object, ...]
    joiner: str = "or"  # key of a fragment: "or" or "and"


# Occurrences shown per finding in the answer of an import; the others are read page by page
# (``GET /api/import/{id}/findings/{index}/occurrences``) or exported (Sprint 4, lot 3).
MAX_OCCURRENCES = 25
# Occurrences kept per finding in memory, for the pages and the export. Beyond, only the total is
# kept, and the answer says how many are available (load test of 30/10: 3.5 million rows).
MAX_STORED_OCCURRENCES = 200_000
# Characters of a register value copied into a finding (occurrence, details, parameter). The data
# model allows 255 at most; beyond this length the copy is cut and says how many characters are
# left out. A single 300 MB cell made an answer of 1.2 GB (red team RT-18).
MAX_VALUE_LENGTH = 1_000


def clip(value: str) -> str:
    """The value, cut to MAX_VALUE_LENGTH characters with the number of characters left out."""
    if len(value) <= MAX_VALUE_LENGTH:
        return value
    return f"{value[:MAX_VALUE_LENGTH]}… (+{len(value) - MAX_VALUE_LENGTH})"


@dataclass(frozen=True, slots=True)
class Occurrence:
    """Where a finding was seen in the data.

    ``row`` is the rank of the data row, the header excluded (first data row = 1).
    """

    table: str | None = None
    row: int | None = None
    column: str | None = None
    value: str | None = None
    # Cross-table checks (Sprint 3): where the value was expected, and which side of a
    # contradiction this occurrence is ("source", "target"); None for single-table checks.
    target_table: str | None = None
    target_column: str | None = None
    side: str | None = None

    def __post_init__(self) -> None:
        if self.value is not None and len(self.value) > MAX_VALUE_LENGTH:
            object.__setattr__(self, "value", clip(self.value))


@dataclass(frozen=True)
class ValidationMessage:
    """One finding, independent of any language."""

    code: str
    severity: Severity
    params: Mapping[str, object] = field(default_factory=dict)
    # Raw technical detail (a path, a parser message) or a fragment to translate.
    details: str | Fragment | None = None
    # Codes used by the authorities for the same finding (e.g. "EBA.808").
    official_codes: tuple[str, ...] = ()
    # The places where the finding was seen (at most MAX_STORED_OCCURRENCES; the answer of an
    # import shows the first MAX_OCCURRENCES).
    occurrences: tuple[Occurrence, ...] = ()
    # Real number of occurrences, which may exceed those kept (0 = not counted).
    occurrences_total: int = 0


def with_occurrences(
    message: ValidationMessage, occurrences: Iterable[Occurrence], total: int | None = None
) -> ValidationMessage:
    """Attach occurrences, keeping the first MAX_STORED_OCCURRENCES and the real total."""
    found = tuple(occurrences)
    return replace(
        message,
        occurrences=found[:MAX_STORED_OCCURRENCES],
        occurrences_total=max(total if total is not None else 0, len(found)),
    )


@dataclass(frozen=True)
class Reference:
    """Source of a control, in a given language."""

    type: ReferenceType
    text: str
    # False when the source has not been read first-hand and must be confirmed.
    verified: bool = True


@dataclass(frozen=True)
class RenderedMessage:
    """A finding written in one language, ready to be displayed."""

    code: str
    severity: Severity
    message: str
    details: str | None
    explanation: str | None
    recommendation: str | None
    expert_advice: str | None
    reference: Reference | None
    official_codes: tuple[str, ...]
    # CONFIRMED (backed by a source read first-hand, or a technical impossibility),
    # PROVISIONAL (no such source yet) or PO_VALIDATED (decision of the Product Owner).
    severity_status: str = "CONFIRMED"
    # Main code used by the authority (first of ``official_codes``), if any.
    authority_code: str | None = None
    occurrences: tuple[Occurrence, ...] = ()
    occurrences_total: int = 0
    # Occurrences kept in memory, readable page by page (≤ total; < total beyond the cap).
    occurrences_available: int = 0
    # Severity published by the EBA ("warning", "error") when the finding applies one of its
    # validation rules, shown next to ours (PO, #179).
    eba_severity: str | None = None


# ----------------------------------------------------------------- data files
@lru_cache
def load_catalog() -> dict[str, JsonDict]:
    """Language-independent definition of every finding."""
    return cast(
        dict[str, JsonDict], json.loads((CATALOG_DIR / CATALOG_FILE).read_text(encoding="utf-8"))
    )


@lru_cache
def load_texts(language: str = DEFAULT_LANGUAGE) -> JsonDict:
    """Texts of one language (read once per process)."""
    return cast(
        JsonDict, json.loads((CATALOG_DIR / f"{language}.json").read_text(encoding="utf-8"))
    )


@lru_cache
def supported_languages() -> tuple[str, ...]:
    """Languages for which a text file exists, the default one first."""
    found = sorted(p.stem for p in CATALOG_DIR.glob("*.json") if p.name != CATALOG_FILE)
    return (DEFAULT_LANGUAGE, *[code for code in found if code != DEFAULT_LANGUAGE])


def resolve_language(*candidates: str | None) -> str:
    """Pick the first supported language among the candidates.

    Each candidate may be a language code (``fr``), a locale (``fr-FR``) or an
    ``Accept-Language`` header (``fr-FR,fr;q=0.9,en;q=0.8``).
    """
    for candidate in candidates:
        for part in (candidate or "").split(","):
            code = part.split(";")[0].strip().lower().split("-")[0]
            if code in supported_languages():
                return code
    return DEFAULT_LANGUAGE


# ------------------------------------------------------------------- building
def make_message(
    code: str, details: str | Fragment | None = None, **params: object
) -> ValidationMessage:
    """Create a finding. ``params`` fill the ``{placeholders}`` of its texts.

    Parameters must never carry register data other than what the user needs to
    locate the finding (a file name, a template code).
    """
    entry = load_catalog()[code]
    return ValidationMessage(
        code=code,
        severity=Severity(entry["severity"]),
        params={
            name: clip(value) if isinstance(value, str) else value for name, value in params.items()
        },
        details=_clip_details(details),
        official_codes=tuple(entry.get("official_codes", [])),
    )


def _clip_details(details: str | Fragment | None) -> str | Fragment | None:
    """Each line of the details cut to MAX_VALUE_LENGTH characters (a line may quote a value)."""
    if not isinstance(details, str) or len(details) <= MAX_VALUE_LENGTH:
        return details
    return "\n".join(clip(line) for line in details.split("\n"))


def has_blocker(messages: list[ValidationMessage]) -> bool:
    """Tell whether at least one message is a BLOCKER."""
    return any(m.severity is Severity.BLOCKER for m in messages)


def split_messages(
    messages: list[ValidationMessage],
) -> tuple[list[ValidationMessage], list[ValidationMessage]]:
    """Split messages into errors (BLOCKER, MAJOR) and warnings (MINOR, INFO)."""
    errors = [m for m in messages if m.severity in (Severity.BLOCKER, Severity.MAJOR)]
    warnings = [m for m in messages if m.severity in (Severity.MINOR, Severity.INFO)]
    return errors, warnings


# ------------------------------------------------------------------ rendering
def _lookup(section: str, key: str, language: str) -> str | None:
    """Text of a key, falling back to the default language when it is missing."""
    for candidate in (language, DEFAULT_LANGUAGE):
        value = load_texts(candidate).get(section, {}).get(key)
        if value:
            return str(value)
    return None


def render_fragment(value: object, language: str) -> object:
    """Write a fragment, a label or a list in a language. Any other value is unchanged."""
    if isinstance(value, Label):
        text = data_model.label(value.kind, value.code, language)
        if text is None:
            return value.code
        key = "member_label" if value.kind == "member" else "field_label"
        template = _lookup("fragments", key, language) or "{label}"
        return template.format(label=text, code=value.code)
    if isinstance(value, Joined):
        parts = [str(render_fragment(part, language)) for part in value.parts]
        if len(parts) < 2:
            return "".join(parts)
        word = _lookup("fragments", value.joiner, language) or value.joiner
        return ", ".join(parts[:-1]) + f" {word} " + parts[-1]
    if not isinstance(value, Fragment):
        return value
    template = _lookup("fragments", value.key, language) or value.key
    return template.format(**{k: render_fragment(v, language) for k, v in value.params.items()})


def render_text(section: str, key: str, language: str, **params: object) -> str:
    """Write a standalone text (step name, API error) in a language."""
    template = _lookup(section, key, language) or key
    return template.format(**params)


def render_message(message: ValidationMessage, language: str = DEFAULT_LANGUAGE) -> RenderedMessage:
    """Write a finding in a language."""
    entry = load_catalog()[message.code]
    params = {name: render_fragment(value, language) for name, value in message.params.items()}

    def text(field_name: str, formatted: bool = True) -> str | None:
        texts = load_texts(language).get("messages", {}).get(message.code, {})
        value = texts.get(field_name) or load_texts(DEFAULT_LANGUAGE)["messages"][message.code].get(
            field_name
        )
        if not value:
            return None
        return str(value.format(**params) if formatted else value)

    reference = entry.get("reference")
    details = render_fragment(message.details, language)
    return RenderedMessage(
        code=message.code,
        severity=message.severity,
        message=text("message") or message.code,
        details=str(details) if details is not None else None,
        explanation=text("explanation"),
        recommendation=text("recommendation"),
        # Advice is fixed text: it is not formatted, so it may contain braces.
        expert_advice=text("expert_advice", formatted=False),
        reference=Reference(
            type=ReferenceType(reference["type"]),
            text=_lookup("references", reference["key"], language) or reference["key"],
            verified=reference.get("verified", True),
        )
        if reference
        else None,
        official_codes=message.official_codes,
        severity_status=entry.get("severity_status", "CONFIRMED"),
        authority_code=message.official_codes[0] if message.official_codes else None,
        occurrences=message.occurrences[:MAX_OCCURRENCES],
        occurrences_total=max(message.occurrences_total, len(message.occurrences)),
        occurrences_available=len(message.occurrences),
        eba_severity=data_model.eba_severity(message.official_codes),
    )
