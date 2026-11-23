# SPDX-License-Identifier: EUPL-1.2
import json

import pytest

from contracts.messages import Severity
from import_engine.package_validator import PackageValidator, cross_check_envelope
from tests import factories
from tests.conftest import codes


def validate(write, name=f"{factories.PACKAGE_NAME}.zip", **options):
    return PackageValidator().validate(write(name, factories.build_zip(**options)))


def with_file(path: str, content: bytes | None) -> dict[str, bytes]:
    files = factories.default_files()
    if content is None:
        del files[path]
    else:
        files[path] = content
    return files


def test_valid_package_has_no_finding_and_full_metadata(write) -> None:
    result = validate(write)

    assert result.messages == []
    assert result.taxonomy_version == "4.0"
    assert len(result.rt_detected) == 15 and result.missing_rt == []
    metadata = result.metadata
    assert (metadata.entity_lei, metadata.reporting_scope) == (factories.LEI, "CON")
    assert (metadata.reference_date, metadata.base_currency) == ("2025-12-31", "EUR")
    assert (metadata.country, metadata.module_code) == ("FR", "DORA010100")


def test_archive_without_single_root_folder(write) -> None:
    assert codes(validate(write, root=None).messages) == ["PKG-001"]
    assert codes(validate(write, extra={"readme.txt": b"x"}).messages) == ["PKG-001"]


def test_naming_convention_and_zip_name(write) -> None:
    assert codes(validate(write, root="my-register").messages) == ["PKG-002", "PKG-003"]
    assert codes(validate(write, name="other.zip").messages) == ["PKG-002"]
    # An archive extracted from an envelope has no file name to compare.
    assert validate(write, name="package.zip").messages == []


def test_unexpected_folder_and_files_are_blocking(write) -> None:
    files = factories.default_files()
    files["reports/register.xlsx"] = b"x"
    files["docs/notes.txt"] = b"x"
    files["META-INF/extra.json"] = b"{}"

    result = validate(write, files=files)

    assert sorted(codes(result.messages)) == ["PKG-004", "PKG-007", "PKG-007", "PKG-007"]
    assert not result.valid


def test_missing_mandatory_files(write) -> None:
    files = factories.default_files()
    for path in ("META-INF/reportPackage.json", "reports/report.json", "reports/parameters.csv"):
        del files[path]

    assert codes(validate(write, files=files).messages) == ["PKG-005"] * 3


def test_unsupported_taxonomy_version(write) -> None:
    report = {
        "documentInfo": {
            "documentType": "https://xbrl.org/2021/xbrl-csv",
            "extends": ["http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/dora/4.4/mod/dora.json"],
        }
    }

    result = validate(write, files=with_file("reports/report.json", json.dumps(report).encode()))

    assert codes(result.messages) == ["PKG-009"]
    assert result.taxonomy_version == "4.4"
    assert result.valid, "an unknown version is a MAJOR, the import goes on"


def test_invalid_json_and_parameters(write) -> None:
    assert codes(
        validate(write, files=with_file("reports/report.json", b"{not json")).messages
    ) == ["PKG-006"]

    parameters = (
        b"name,value\nentityID,LEI123\nrefPeriod,31/12/2025\nbaseCurrency,iso4217:EUR\n"
        b"decimalsInteger,0\ndecimalsMonetary,-3\ndecimalsPercentage,4\n"
    )
    result = validate(write, files=with_file("reports/parameters.csv", parameters))

    assert codes(result.messages) == ["PKG-014", "PKG-014", "PKG-015"]


def test_missing_template_is_informational_and_listed(write) -> None:
    # A partial filing is accepted when its indicator is declared (PO-29, #99).
    from contracts.messages import Severity

    result = validate(write, files=with_file("reports/b_99.01.csv", None))

    assert codes(result.messages) == ["PKG-010"]
    assert result.missing_rt == ["B_99.01"]
    assert result.messages[0].severity is Severity.INFO
    assert result.valid


def test_missing_template_without_its_indicator_stays_blocking(write) -> None:
    files = with_file("reports/b_99.01.csv", None)
    files["reports/FilingIndicators.csv"] = files["reports/FilingIndicators.csv"].replace(
        b"B_99.01,true\n", b""
    )

    result = validate(write, files=files)

    assert codes(result.messages) == ["PKG-010", "PKG-011"]
    assert not result.valid


def test_filing_indicators(write) -> None:
    indicators = "templateID,reported\n" + "".join(
        f"{code},true\n" for code in factories.TEMPLATES[3:]
    )
    indicators += "B_01.02,TRUE\nB_01.03,false\nB_42.00,true\n"

    result = validate(write, files=with_file("reports/FilingIndicators.csv", indicators.encode()))

    assert sorted(codes(result.messages)) == ["PKG-011", "PKG-012", "PKG-013", "PKG-020"]


def test_filing_indicator_one_is_accepted_with_warning(write) -> None:
    indicators = "templateID,reported\n" + "".join(f"{c},1\n" for c in factories.TEMPLATES)

    result = validate(write, files=with_file("reports/FilingIndicators.csv", indicators.encode()))

    assert set(codes(result.messages)) == {"PKG-022"}
    assert all(m.severity.value == "MINOR" for m in result.messages)


def test_filing_indicator_upper_case_is_rejected(write) -> None:
    indicators = "templateID,reported\n" + "".join(
        f"{c},{'TRUE' if i == 0 else 'true'}\n" for i, c in enumerate(factories.TEMPLATES)
    )

    result = validate(write, files=with_file("reports/FilingIndicators.csv", indicators.encode()))

    assert codes(result.messages) == ["PKG-013"]


def test_undeclared_file_is_rejected(write) -> None:
    files = factories.default_files()
    files["reports/Notes.xlsx"] = b"x\n"

    assert "PKG-007" in codes(validate(write, files=files).messages)


def test_footnotes_file_is_accepted_and_ignored_with_an_information(write) -> None:
    # PO-30 (#100): FootNotes.csv is an XBRL file the EBA ignores.
    from contracts.messages import Severity

    files = factories.default_files()
    files["reports/FootNotes.csv"] = b"x\n"

    result = validate(write, files=files)

    assert codes(result.messages) == ["PKG-026"]
    assert result.messages[0].severity is Severity.INFO
    assert result.valid


def test_identity_and_case_rules_are_blocking(write) -> None:
    from contracts.messages import Severity

    files = factories.default_files()
    files["reports/B_02.01.csv"] = files["reports/b_02.01.csv"]
    messages = validate(write, files=files).messages

    assert {m.code: m.severity for m in messages}["PKG-018"] is Severity.BLOCKER


def test_upper_case_file_name_and_duplicate(write) -> None:
    files = factories.default_files()
    files["reports/B_02.01.csv"] = files["reports/b_02.01.csv"]

    assert sorted(codes(validate(write, files=files).messages)) == ["PKG-008", "PKG-018"]


def test_name_must_match_parameters(write) -> None:
    root = "OTHERLEI000000000099.IND_FR_DORA010200_DORA_2024-12-31_20260315120000000"

    result = validate(write, name=f"{root}.zip", root=root)

    assert sorted(codes(result.messages)) == ["PKG-016", "PKG-017", "PKG-019", "PKG-021"]


def test_envelope_sender_must_match_package_entity(write) -> None:
    metadata = validate(write).metadata

    assert cross_check_envelope(factories.LEI, metadata) == []
    assert codes(cross_check_envelope("OTHERLEI000000000099", metadata)) == ["ENV-009"]


def parameters_with(**values: str) -> bytes:
    base = {
        "entityID": f"rs:{factories.LEI}.CON",
        "refPeriod": "2025-12-31",
        "baseCurrency": "iso4217:EUR",
        "decimalsInteger": "0",
        "decimalsMonetary": "-3",
    }
    base.update(values)
    return ("name,value\n" + "".join(f"{k},{v}\n" for k, v in base.items())).encode()


@pytest.mark.parametrize("monetary", ["-4", "-3", "-2", "0", "2"])
def test_monetary_decimals_accepted(write, monetary: str) -> None:
    files = with_file("reports/parameters.csv", parameters_with(decimalsMonetary=monetary))
    assert "PKG-023" not in codes(validate(write, files=files).messages)


@pytest.mark.parametrize("monetary", ["-5", "-6", "-10"])
def test_monetary_decimals_too_low(write, monetary: str) -> None:
    files = with_file("reports/parameters.csv", parameters_with(decimalsMonetary=monetary))
    result = validate(write, files=files)
    assert codes(result.messages).count("PKG-023") == 1


@pytest.mark.parametrize("integer", ["-3", "2"])
def test_integer_decimals_must_be_zero(write, integer: str) -> None:
    files = with_file("reports/parameters.csv", parameters_with(decimalsInteger=integer))
    assert "PKG-023" in codes(validate(write, files=files).messages)


@pytest.mark.parametrize("name", ["decimalsInteger", "decimalsMonetary"])
def test_inf_decimals_accepted(write, name: str) -> None:
    """PO-18 : INF (filing rule 2.18) est accepté, ni PKG-014 ni PKG-023."""
    files = with_file("reports/parameters.csv", parameters_with(**{name: "INF"}))
    found = codes(validate(write, files=files).messages)
    assert "PKG-014" not in found and "PKG-023" not in found


@pytest.mark.parametrize("value", ["inf", "-INF", "INF "])
def test_inf_variants_rejected(write, value: str) -> None:
    files = with_file("reports/parameters.csv", parameters_with(decimalsMonetary=value))
    assert "PKG-014" in codes(validate(write, files=files).messages)


def test_invalid_decimals_stay_a_format_error(write) -> None:
    files = with_file("reports/parameters.csv", parameters_with(decimalsMonetary="abc"))
    found = codes(validate(write, files=files).messages)
    assert "PKG-014" in found and "PKG-023" not in found


def test_macos_metadata_is_ignored_with_an_information(write) -> None:
    # A zip recompressed on a Mac adds __MACOSX/ next to the package folder (bug #82, A1).
    extra = {
        "__MACOSX/._package": b"x",
        f"__MACOSX/{factories.PACKAGE_NAME}/._report.json": b"x",
        ".DS_Store": b"x",
        f"{factories.PACKAGE_NAME}/.DS_Store": b"x",
        f"{factories.PACKAGE_NAME}/reports/._parameters.csv": b"x",
    }

    result = validate(write, extra=extra)

    assert codes(result.messages) == ["PKG-024"]
    assert result.messages[0].severity is Severity.INFO
    assert result.messages[0].params["count"] == "5"
    assert result.valid
    assert result.metadata.package_name == factories.PACKAGE_NAME


def test_backslash_path_is_tolerated_with_a_warning(write) -> None:
    # A6 (#82): "\" is not the ZIP separator; the package is read but a warning is raised.
    files = factories.default_files()
    files["reports\\parameters.csv"] = files.pop("reports/parameters.csv")

    result = validate(write, files=files)

    assert codes(result.messages) == ["PKG-025"]
    assert result.messages[0].severity is Severity.MINOR
    assert result.messages[0].params["count"] == "1"
    assert result.valid
