# SPDX-License-Identifier: EUPL-1.2
"""Reference of national identifier formats (VAT, company numbers), issue #41."""

import json
import re
from pathlib import Path

import pytest

FILE = Path(__file__).resolve().parents[1] / "reference" / "dora" / "national-identifiers.json"
DATA = json.loads(FILE.read_text("utf-8"))
EU = set(
    [
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    ]
)


def entries():
    for country, item in DATA["countries"].items():
        if "vat" in item:
            yield country, "vat", item["vat"]
        for crn in item.get("crn", []):
            yield country, crn["name"], crn


def test_covers_eu_northern_ireland_uk_and_switzerland() -> None:
    assert set(DATA["countries"]) == EU | {"XI", "GB", "CH"}
    assert all("vat" in item for item in DATA["countries"].values())


@pytest.mark.parametrize(("country", "name", "entry"), list(entries()))
def test_entries_are_well_formed(country, name, entry) -> None:
    re.compile(entry["pattern"])
    assert entry["status"] in {"CONFIRMED", "A_VERIFIER"}
    assert set(entry["sources"]) <= set(DATA["sources"])
    if entry["status"] == "CONFIRMED":
        assert entry["sources"], f"{country} {name}: confirmed without source"


@pytest.mark.parametrize(
    ("country", "kind", "value", "valid"),
    [
        ("FR", "vat", "FR12394199723", True),
        ("FR", "vat", "FR394199723", False),
        ("BE", "vat", "BE0123456789", True),
        ("NL", "vat", "NL123456789B01", True),
        ("SE", "vat", "SE556677889901", True),
        ("CH", "vat", "CHE-123.456.789 TVA", True),
        ("CH", "vat", "CHE-123.456.789 VAT", False),
        ("AT", "vat", "AT12345678", False),
        ("EL", None, None, None),
    ],
)
def test_vat_examples(country, kind, value, valid) -> None:
    if country not in DATA["countries"]:
        assert country == "EL"  # Greece is GR in the list, EL in the VAT number
        assert DATA["countries"]["GR"]["vat"]["pattern"].startswith("^EL")
        return
    assert bool(re.match(DATA["countries"][country][kind]["pattern"], value)) is valid


@pytest.mark.parametrize(
    ("country", "value"),
    [
        ("FR", "394199723"),
        ("BE", "1234.567.890"),
        ("NL", "12345678"),
        ("FI", "1234567-8"),
        ("AT", "123456b"),
        ("ES", "B12345678"),
        ("CH", "CHE-123.456.789"),
        ("GB", "SC123456"),
    ],
)
def test_company_number_examples(country, value) -> None:
    patterns = [c["pattern"] for c in DATA["countries"][country]["crn"]]
    assert any(re.match(p, value) for p in patterns)
