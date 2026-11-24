# SPDX-License-Identifier: EUPL-1.2
"""Every finding must explain itself, in every language, with the same parameters."""

import string

import pytest

from contracts.messages import (
    DEFAULT_LANGUAGE,
    TEXT_FIELDS,
    ReferenceType,
    Severity,
    fragment,
    load_catalog,
    load_texts,
    make_message,
    render_message,
    resolve_language,
    supported_languages,
)

LANGUAGES = supported_languages()
OTHER_LANGUAGES = [code for code in LANGUAGES if code != DEFAULT_LANGUAGE]


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_english_and_french_are_available() -> None:
    assert LANGUAGES[0] == "en"
    assert "fr" in LANGUAGES


def test_every_definition_is_complete() -> None:
    references = load_texts()["references"]
    for code, entry in load_catalog().items():
        assert Severity(entry["severity"]), code
        assert ReferenceType(entry["reference"]["type"]), code
        assert entry["reference"]["key"] in references, code


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_finding_is_written_in_every_language(language: str) -> None:
    texts = load_texts(language)["messages"]
    for code, entry in load_catalog().items():
        assert code in texts, f"{language}: {code} is not translated"
        for field in ("message", "explanation", "recommendation"):
            assert texts[code].get(field, "").strip(), f"{language}: {code}.{field} is empty"
        # Only INFO messages, which require no action, may have no expert advice.
        if entry["severity"] != "INFO":
            assert texts[code].get("expert_advice", "").strip(), f"{language}: {code} advice"
    assert set(texts) == set(load_catalog()), f"{language}: unknown codes"


@pytest.mark.parametrize("language", OTHER_LANGUAGES)
def test_translations_use_the_same_parameters_as_english(language: str) -> None:
    english, translated = load_texts(), load_texts(language)
    for code, fields in english["messages"].items():
        for field in TEXT_FIELDS:
            if field == "expert_advice" or field not in fields:
                continue
            expected = placeholders(fields[field])
            found = placeholders(translated["messages"][code][field])
            assert found == expected, f"{language}: {code}.{field}"
    for section in ("references", "fragments", "steps"):
        assert set(translated[section]) == set(english[section]), f"{language}: {section}"
        for key, text in english[section].items():
            assert placeholders(translated[section][key]) == placeholders(text), key


def test_a_finding_is_rendered_in_the_language_requested() -> None:
    finding = make_message("PKG-006", file="reports/report.json", reason=fragment("json_invalid"))

    english = render_message(finding, "en")
    french = render_message(finding, "fr")

    assert english.message == "The file reports/report.json is not valid: not valid JSON."
    assert french.message == "Le fichier reports/report.json n'est pas valide\u00a0: JSON invalide."
    assert french.severity is english.severity is Severity.BLOCKER
    assert french.reference.text != english.reference.text
    assert french.expert_advice and french.expert_advice != english.expert_advice


def test_language_is_resolved_from_a_code_a_locale_or_a_header() -> None:
    assert resolve_language("fr") == "fr"
    assert resolve_language("FR-fr") == "fr"
    assert resolve_language(None, "de-DE,fr;q=0.9,en;q=0.8") == "fr"
    assert resolve_language("de", None) == "en"
    assert resolve_language(None, None) == "en"
    # The explicit choice wins over the browser header.
    assert resolve_language("en", "fr-FR") == "en"


def test_occurrences_are_capped_in_the_answer_and_all_kept_in_memory():
    """Since 0.8.3 the cap of 25 applies to the answer; every occurrence stays readable."""
    from contracts.messages import (
        MAX_OCCURRENCES,
        Occurrence,
        make_message,
        render_message,
        with_occurrences,
    )

    base = make_message("FILE-001")
    occurrences = [Occurrence("B_01.01", row=i, column="c0010", value="x") for i in range(1, 41)]
    kept = with_occurrences(base, occurrences)
    assert len(kept.occurrences) == 40
    rendered = render_message(kept, "en")
    assert len(rendered.occurrences) == MAX_OCCURRENCES
    assert rendered.occurrences_total == rendered.occurrences_available == 40
    assert rendered.occurrences[0].row == 1
    # An explicit total larger than what was given is kept.
    assert with_occurrences(base, occurrences[:3], total=100).occurrences_total == 100


def test_rendered_message_carries_structured_fields():
    from contracts.messages import Occurrence, make_message, render_message, with_occurrences

    code = next(c for c, e in load_catalog().items() if e.get("official_codes"))
    message = with_occurrences(make_message(code), [Occurrence("T", 2, "C", "v")])
    rendered = render_message(message, "en")
    assert rendered.authority_code == load_catalog()[code]["official_codes"][0]
    assert rendered.occurrences == message.occurrences
    assert rendered.occurrences_total == 1
    plain = render_message(make_message("FILE-001"), "en")
    assert plain.authority_code is None and plain.occurrences == ()


def test_eba_severity_comes_from_the_eba_list() -> None:
    from contracts.data_model import eba_severity

    assert eba_severity(("EBA.V8825",)) == "warning"
    assert eba_severity(("EBA.v8826", "EBA.v8821")) == "warning"
    assert eba_severity(("EBA.808",)) is None
    assert eba_severity(()) is None


def test_labels_fall_back_to_the_eba_data_model_then_to_the_code() -> None:
    from contracts.messages import field_label, member_label, render_fragment

    # Not in the ITS: the English label of the EBA data model.
    assert render_fragment(member_label("eba_ZZ:x0"), "fr") == "« Not applicable »"
    assert render_fragment(field_label("B_99.99.9999"), "fr") == "B_99.99.9999"


def test_official_labels_cover_the_columns_and_values_used_by_the_eba_rules() -> None:
    from contracts.messages import field_label, member_label, render_fragment

    assert render_fragment(member_label("eba_ZZ:x959"), "fr") == "« Non substituable »"
    assert render_fragment(member_label("eba_ZZ:x959"), "en") == "'Not substitutable'"
    assert render_fragment(field_label("B_07.01.0050"), "fr") == (
        "« Substituabilité du prestataire tiers de services TIC » (B_07.01.0050)"
    )
    # B_06.01: renumbered by the corrigendum of 19/09/2025 (ITS 0060 → 0050), as in the taxonomy.
    assert "criticité" in str(render_fragment(field_label("B_06.01.0050"), "fr"))
    for code in ("eba_CO:x3", "eba_CT:x317", "eba_CT:x318", "eba_ZZ:x960"):
        assert render_fragment(member_label(code), "fr") != render_fragment(
            member_label(code), "en"
        )


def test_corrigendum_of_2025_is_applied_to_the_labels() -> None:
    from contracts.messages import field_label, render_fragment

    assert str(render_fragment(field_label("B_05.01.0090"), "fr")).startswith(
        "« Monnaie du montant déclaré dans la colonne B_05.01.0100 »"
    )


def test_language_code_cannot_reach_another_file() -> None:
    # CodeQL py/path-injection: the file is chosen among the files present, never built from
    # the requested code.
    import pytest

    from contracts.messages import load_texts

    for code in ("../catalog", "../../pyproject", "fr/../en", "/etc/passwd", "catalog"):
        with pytest.raises(ValueError, match="Unsupported language"):
            load_texts(code)
    assert load_texts("fr")["messages"]
