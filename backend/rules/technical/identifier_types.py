# SPDX-License-Identifier: EUPL-1.2
"""Consistency between an identifier and its declared type of code (PO-5, issue #8).

Checks, for the columns typed by a "type of code" column:

- DAT-014: the value does not fit its declared type but clearly looks like another one
  (a French VAT number declared as EUID, a valid LEI declared as passport number...);
- DAT-016: a French EUID is FR + register code (e.g. RCSPARIS) + optional dot + SIREN;
- DAT-017: a company registration number (CRN) fits the national format: SIREN (9 digits)
  or SIRET (14 digits) in France, otherwise the formats of national-identifiers.json;
- DAT-018: the VAT number fits the national format: FR + 2-digit key + SIREN in France,
  otherwise the formats of national-identifiers.json;
- DAT-019: the additional code of a provider that is not declared a natural person
  (B_05.01.0070) is never a national code or a passport number (decision of the PO, 02/11/2026);
- DAT-020: the additional code is not the same as the main code (B_05.01.0010);
- DAT-021: a branch code (B_01.03.0010) is not the LEI of its head office (B_01.03.0020);
- DAT-034: a natural person (B_05.01.0070) has no EUID, as main or additional code (the EUID
  identifies companies and branches only, regulation 2021/1042);
- DAT-035: a natural person declared with a LEI, as main or additional code: possible (GLEIF
  issues LEIs to individuals acting in a business capacity) but rare, so worth a check.

The country comes from B_05.01.0080 (headquarters) on the same row, so DAT-017 / DAT-018
only apply to B_05.01.0010 and 0030. Outside France, a country is checked only when all its
formats are CONFIRMED in the reference (sources of docs/methode.md); the others are not
checked yet.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import polars as pl

from contracts import data_model, identifiers
from contracts.dataset import RoIDataset
from contracts.messages import ValidationMessage
from contracts.tables import column_values
from rules.technical.identifiers import EUID_ENTITY_COUNTRY, _finding
from rules.technical.locations import Hit, hit

ROW_COLUMN = "_row"
FRANCE = "FR"
NATURAL_PERSON = "eba_CT:x213"
# Code and type columns of B_05.01: main code, then additional code.
PROVIDER_CODES = (("c0010", "c0020"), ("c0030", "c0040"))
NATIONAL_IDENTIFIERS = (
    Path(__file__).resolve().parents[2] / "reference" / "dora" / "national-identifiers.json"
)


@lru_cache(maxsize=1)
def _national_formats() -> dict[str, dict]:
    """Formats of the national reference, kept only where every format is CONFIRMED.

    A country (or a kind of number) whose format is still A_VERIFIER is not checked (issue #41).
    """
    countries = json.loads(NATIONAL_IDENTIFIERS.read_text("utf-8"))["countries"]
    formats: dict[str, dict] = {}
    for code, entry in countries.items():
        crn = entry.get("crn") or []
        vat = entry.get("vat")
        formats[code] = {
            "crn": [re.compile(item["pattern"]) for item in crn]
            if crn and all(item["status"] == "CONFIRMED" for item in crn)
            else None,
            "vat": re.compile(vat["pattern"]) if vat and vat["status"] == "CONFIRMED" else None,
        }
    return formats


def _text(frame: pl.DataFrame, column: str, index: int) -> str:
    if column not in frame.columns:
        return ""
    value = column_values(frame, column)[index]
    return "" if value is None else str(value)


def _countries() -> dict[tuple[str, str], str]:
    return {
        (table, column): country
        for table, columns, country in EUID_ENTITY_COUNTRY
        for column in columns
    }


CODES = (
    "DAT-014",
    "DAT-016",
    "DAT-017",
    "DAT-018",
    "DAT-019",
    "DAT-020",
    "DAT-021",
    "DAT-034",
    "DAT-035",
)


class IdentifierTypeRule:
    id = "IDENTIFIER_TYPE"
    codes = CODES

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        found: dict[str, dict[tuple[str, str], list[Hit]]] = {}

        def add(code: str, table: str, column: str, line: Hit) -> None:
            found.setdefault(code, {}).setdefault((table, column), []).append(line)

        countries = _countries()
        for table, column, type_column in data_model.identifier_fields().typed:
            frame = dataset.tables.get(table)
            if frame is None or column not in frame.columns:
                continue
            country_column = countries.get((table, column))
            # Columns read once, as lists (load test of 30/10: 3.5 million rows).
            present = frame.columns
            values = column_values(frame, column)
            types = column_values(frame, type_column) if type_column in present else None
            country_values = (
                column_values(frame, country_column)
                if country_column and country_column in present
                else None
            )
            for index, row in enumerate(column_values(frame, ROW_COLUMN)):
                raw = values[index]
                value = "" if raw is None else str(raw).strip()
                kind = identifiers.TYPE_KINDS.get(types[index]) if types is not None else None
                if not value or kind is None:
                    continue
                place = hit(row, value)
                other = identifiers.looks_like_other_kind(value, kind)
                if other:
                    add("DAT-014", table, column, hit(row, value, f" : {kind} → {other}"))
                    continue
                country = ""
                if country_values is not None:
                    country = str(country_values[index] or "").rsplit(":", 1)[-1].upper()
                self._french(add, table, column, place, value, kind, country)

        self._additional_code(dataset, add)
        self._branches(dataset, add)
        messages: list[ValidationMessage] = []
        for code in CODES:
            messages += _finding(code, found.get(code, {}))
        return messages

    @staticmethod
    def _french(add, table, column, place, value, kind, country) -> None:
        if kind == identifiers.KIND_EUID:
            analysis = identifiers.analyse_euid(value)
            if analysis.country == FRANCE and not identifiers.FRENCH_EUID.match(value.upper()):
                add("DAT-016", table, column, place)
        elif country == FRANCE:
            if kind == identifiers.KIND_CRN and not identifiers.is_french_national_number(value):
                add("DAT-017", table, column, place)
            elif kind == identifiers.KIND_VAT and not identifiers.FRENCH_VAT.match(value):
                add("DAT-018", table, column, place)
        elif kind in (identifiers.KIND_CRN, identifiers.KIND_VAT):
            formats = _national_formats().get(country)
            if formats is None:
                return
            if kind == identifiers.KIND_CRN:
                patterns = formats["crn"]
                if patterns and not any(p.match(value) for p in patterns):
                    add("DAT-017", table, column, place)
            elif formats["vat"] and not formats["vat"].match(value):
                add("DAT-018", table, column, place)

    @staticmethod
    def _additional_code(dataset: RoIDataset, add) -> None:
        frame = dataset.tables.get("B_05.01")
        if frame is None:
            return
        for index, row in enumerate(frame[ROW_COLUMN]):
            main = _text(frame, "c0010", index).strip()
            additional = _text(frame, "c0030", index).strip()
            additional_type = _text(frame, "c0040", index)
            natural = _text(frame, "c0070", index) == NATURAL_PERSON
            # A natural person may use a national code or a passport (ITS, annex I, B_05.01.0040).
            # An empty type of person is reported by DAT-023: the check then stays as strict.
            if additional_type in identifiers.FORBIDDEN_ADDITIONAL_TYPES and not natural:
                add("DAT-019", "B_05.01", "c0040", hit(row, additional_type))
            if additional and additional == main:
                add("DAT-020", "B_05.01", "c0030", hit(row, additional))
            if natural:
                for code_column, type_column in PROVIDER_CODES:
                    if not _text(frame, code_column, index).strip():
                        continue
                    code_type = _text(frame, type_column, index)
                    kind = identifiers.TYPE_KINDS.get(code_type)
                    if kind == identifiers.KIND_EUID:
                        add("DAT-034", "B_05.01", type_column, hit(row, code_type))
                    elif kind == identifiers.KIND_LEI:
                        add("DAT-035", "B_05.01", type_column, hit(row, code_type))

    @staticmethod
    def _branches(dataset: RoIDataset, add) -> None:
        frame = dataset.tables.get("B_01.03")
        if frame is None:
            return
        for index, row in enumerate(frame[ROW_COLUMN]):
            branch = _text(frame, "c0010", index).strip()
            if branch and branch == _text(frame, "c0020", index).strip():
                add("DAT-021", "B_01.03", "c0010", hit(row, branch))
