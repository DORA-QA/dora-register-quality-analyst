# SPDX-License-Identifier: EUPL-1.2
"""Format of the identifiers found in a register: LEI (ISO 17442) and EUID.

Pure functions: no dataset, no file, no network. They analyse one raw value and
say what is wrong with it. They never change the value and never look an
identifier up in a registry (existence is not checked, nothing leaves the machine).
"""

import re
from dataclasses import dataclass
from functools import lru_cache

LEI_LENGTH = 20
LEI_ALLOWED = re.compile(r"^[A-Z0-9]+$")
# 18 characters, then 2 check digits: the mask published in the EBA validation rules.
LEI_MASK = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")

LEI_OK = "ok"
LEI_LENGTH_WRONG = "length"
LEI_BAD_CHARACTERS = "characters"
LEI_BAD_MASK = "mask"
LEI_BAD_CHECKSUM = "checksum"


# ISO 7064: letters become numbers (A=10 ... Z=35), digits stay as they are. A translation
# table does it in one native pass (load test of 30/10: 1.2 million identifiers).
_LETTERS_TO_NUMBERS = str.maketrans(
    {letter: str(10 + index) for index, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
    | {letter: str(10 + index) for index, letter in enumerate("abcdefghijklmnopqrstuvwxyz")}
)
_INNER_SPACE = re.compile(r"\s")


def _to_digits(value: str) -> str:
    """ISO 7064: letters become numbers (A=10 ... Z=35), digits stay as they are."""
    return value.translate(_LETTERS_TO_NUMBERS)


def lei_checksum_is_valid(value: str) -> bool:
    """ISO 17442 / ISO 7064 MOD 97-10: the number built from the 20 characters is 1 modulo 97.

    The value must already respect the mask; anything else returns False.
    """
    if not LEI_MASK.match(value):
        return False
    return int(_to_digits(value)) % 97 == 1


def lei_check_digits(first_18: str) -> str:
    """Check digits for the first 18 characters (used to build test identifiers)."""
    return f"{98 - int(_to_digits(first_18 + '00')) % 97:02d}"


@dataclass(frozen=True)
class LeiAnalysis:
    """What is wrong with a LEI. ``problem`` is judged on the value without whitespace."""

    leading_spaces: bool
    trailing_spaces: bool
    inner_spaces: bool
    # The value with every whitespace removed, shown to explain, never stored back.
    normalized: str
    # One of the LEI_* constants: the first problem found, in the order
    # length, characters, mask, check digits. The mask is always checked before the check digits.
    problem: str

    @property
    def has_whitespace(self) -> bool:
        return self.leading_spaces or self.trailing_spaces or self.inner_spaces


@lru_cache(maxsize=65536)  # pure; a register repeats a few identifiers many times
def analyse_lei(value: str) -> LeiAnalysis:
    normalized = "".join(value.split())
    stripped = value.strip()
    if len(normalized) != LEI_LENGTH:
        problem = LEI_LENGTH_WRONG
    elif not LEI_ALLOWED.match(normalized):
        problem = LEI_BAD_CHARACTERS
    elif not LEI_MASK.match(normalized):
        problem = LEI_BAD_MASK
    elif not lei_checksum_is_valid(normalized):
        problem = LEI_BAD_CHECKSUM
    else:
        problem = LEI_OK
    return LeiAnalysis(
        leading_spaces=value != value.lstrip(),
        trailing_spaces=value != value.rstrip(),
        inner_spaces=bool(_INNER_SPACE.search(stripped)),
        normalized=normalized,
        problem=problem,
    )


# --------------------------------------------------------------------- EUID
EUID_OK = "ok"
EUID_WHITESPACE = "whitespace"
EUID_BAD_CHARACTERS = "characters"
EUID_EMPTY_PART = "empty_part"
EUID_BAD_PREFIX = "prefix"


@dataclass(frozen=True)
class EuidAnalysis:
    problem: str
    # Two letters in front of the identifier, upper-cased, None when the syntax is wrong.
    country: str | None


@lru_cache(maxsize=65536)
def analyse_euid(value: str) -> EuidAnalysis:
    """Syntax of an EUID: ``<country><code>`` or ``<country><registry>.<number>``.

    The dot is optional (real registers omit it). Checked: no whitespace, two letters
    for the country, then one non-empty code of letters and digits (at most one dot,
    never at either end). Whether the country is in the EEA, or the right one for the
    entity, are other questions, see ``rules/technical/identifiers.py``.
    """
    if _INNER_SPACE.search(value):
        return EuidAnalysis(EUID_WHITESPACE, None)
    if not re.match(r"^[A-Za-z]{2}", value):
        return EuidAnalysis(EUID_BAD_PREFIX, None)
    code = value[2:]
    parts = code.split(".")
    if len(parts) > 2 or not all(parts):
        return EuidAnalysis(EUID_EMPTY_PART, None)
    if not all(part.isascii() and part.isalnum() for part in parts):
        return EuidAnalysis(EUID_BAD_CHARACTERS, None)
    return EuidAnalysis(EUID_OK, value[:2].upper())


def has_registry_separator(value: str) -> bool:
    """The EUID separates the register identifier from the registration number.

    Regulation (EU) 2021/1042 (annex, point 9) requires both elements but no
    separator; the EBA recommends a dot (observations 2025, p. 20). Without one,
    the presence of the register identifier cannot be checked.
    """
    return "." in value


def same_country(first: str, second: str) -> bool:
    """Two ISO 3166 codes designate the same country (Greece is GR or EL)."""
    greece = {"GR", "EL"}
    a, b = first.upper(), second.upper()
    return a == b or {a, b} <= greece


# ------------------------------------------------------- kinds of identifier
KIND_LEI = "LEI"
KIND_EUID = "EUID"
KIND_CRN = "CRN"  # national company number (SIREN or SIRET in France)
KIND_VAT = "VAT"
KIND_OTHER = "OTHER"  # national code, passport number

# Type-of-code member of the EBA list L07 -> kind.
TYPE_KINDS = {
    "eba_qCO:qx2000": KIND_LEI,
    "eba_qCO:qx2002": KIND_EUID,
    "eba_qCO:qx2003": KIND_CRN,
    "eba_qCO:qx2004": KIND_VAT,
    "eba_qCO:qx2001": KIND_OTHER,
    "eba_qCO:qx2005": KIND_OTHER,
}
# Types that must not describe the additional identification code (B_05.01.0040).
FORBIDDEN_ADDITIONAL_TYPES = ("eba_qCO:qx2001", "eba_qCO:qx2005")

FRENCH_VAT = re.compile(r"^FR\d{11}$")  # FR + 2-digit key + SIREN (service-public.gouv.fr)
SIREN = re.compile(r"^\d{9}$")
SIRET = re.compile(r"^\d{14}$")
GENERIC_VAT = re.compile(r"^[A-Za-z]{2}[A-Za-z0-9]+$")
# French EUID: FR + register code (RCS + town, e.g. RCSPARIS) + optional dot + SIREN.
FRENCH_EUID = re.compile(r"^FR[A-Z0-9]+\.?\d{9}$")


def clear_caches() -> None:
    """Forget the identifiers analysed (values of the register) once an import is over.

    The analyses are cached for speed during one import only: nothing read from a register may
    outlive the import in memory (red team RT-02, review of 30/10).
    """
    analyse_lei.cache_clear()
    analyse_euid.cache_clear()
    recognised_kinds.cache_clear()


def is_french_national_number(value: str) -> bool:
    return bool(SIREN.match(value) or SIRET.match(value))


@lru_cache(maxsize=65536)
def recognised_kinds(value: str) -> frozenset[str]:
    """Kinds whose format the value matches without doubt (strong formats only)."""
    text = value.strip()
    kinds: set[str] = set()
    if analyse_lei(text).problem == LEI_OK:
        kinds.add(KIND_LEI)
    if FRENCH_VAT.match(text):
        kinds.add(KIND_VAT)
    elif is_french_national_number(text):
        kinds.add(KIND_CRN)
    elif "." in text and analyse_euid(text).problem == EUID_OK:
        kinds.add(KIND_EUID)
    return frozenset(kinds)


def fits_kind(value: str, kind: str) -> bool:
    """Whether the value is acceptable for the kind, whatever the country."""
    text = value.strip()
    if kind == KIND_LEI:
        return analyse_lei(text).problem == LEI_OK
    if kind == KIND_EUID:
        return analyse_euid(text).problem == EUID_OK and not FRENCH_VAT.match(text)
    if kind == KIND_VAT:
        return bool(GENERIC_VAT.match(text))
    if kind == KIND_CRN:
        return is_french_national_number(text)
    return True


def looks_like_other_kind(value: str, declared: str | None) -> str | None:
    """The kind the value looks like when it does not match the kind declared next to it."""
    if declared is None:
        return None
    kinds = recognised_kinds(value)
    if declared == KIND_OTHER:
        return sorted(kinds)[0] if kinds else None
    if declared in kinds or fits_kind(value, declared):
        return None
    return sorted(kinds)[0] if kinds else None
