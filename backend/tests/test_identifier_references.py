# SPDX-License-Identifier: EUPL-1.2
"""Red team RT-08: every reference of the catalogue is checked against its source.

The identifier controls (DAT-014, DAT-016 to DAT-021) and DAT-029 used to cite "Product Owner
rules" not checked source by source (verified: false). Each now cites the official text it applies
or, for DAT-020, says plainly that it is a rule of the product.
"""

from contracts.messages import load_catalog, load_texts

OFFICIAL = {
    "DAT-014": "its_annex_i_b0501_0010",
    "DAT-016": "bris_2021_1042",
    "DAT-017": "dila_siren_siret",
    "DAT-018": "dila_vat_number",
    "DAT-019": "its_annex_i_b0501_0040",
    "DAT-021": "its_annex_i_b0103_0010",
    "DAT-029": "its_annex_i_b0201_0030",
}


def test_no_reference_is_left_unverified() -> None:
    unverified = [
        code for code, entry in load_catalog().items() if not entry["reference"]["verified"]
    ]
    assert unverified == []


def test_identifier_controls_cite_their_official_source() -> None:
    catalog = load_catalog()
    for code, key in OFFICIAL.items():
        assert catalog[code]["reference"]["key"] == key, code
        assert catalog[code]["reference"]["type"] != "product", code


def test_the_rule_without_official_basis_is_declared_as_a_product_rule() -> None:
    reference = load_catalog()["DAT-020"]["reference"]
    assert (reference["key"], reference["type"]) == ("po_additional_code", "product")


def test_references_quote_the_column_they_apply() -> None:
    for language in ("fr", "en"):
        references = load_texts(language)["references"]
        assert "po_identifier_rules" not in references
        for key, column in (
            ("its_annex_i_b0501_0010", "B_05.01.0010"),
            ("its_annex_i_b0501_0040", "B_05.01.0040"),
            ("its_annex_i_b0103_0010", "B_01.03.0010"),
            ("its_annex_i_b0201_0030", "B_02.01.0030"),
            ("dila_siren_siret", "F32135"),
            ("dila_vat_number", "F23570"),
        ):
            assert column in references[key], (language, key)
