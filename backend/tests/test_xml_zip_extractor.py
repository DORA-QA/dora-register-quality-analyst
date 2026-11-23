# SPDX-License-Identifier: EUPL-1.2
import zipfile

import pytest

from import_engine.onegate import check_onegate_target, is_acpr
from import_engine.xml_zip_extractor import XmlZipExtractor
from tests import factories
from tests.conftest import codes


def extract(write, **options):
    return XmlZipExtractor().extract_zip(write("envelope.xml", factories.build_envelope(**options)))


def test_package_is_extracted_from_a_onegate_envelope(write) -> None:
    result = extract(write)

    assert result.valid and result.messages == []
    assert result.strategy == "ACPR_ONEGATE"
    assert result.sender_lei == factories.LEI
    assert result.domain == "DRB"
    with zipfile.ZipFile(result.zip_path) as archive:
        assert f"{factories.PACKAGE_NAME}/reports/report.json" in archive.namelist()


def test_base64_split_over_several_lines_is_accepted(write) -> None:
    import base64

    encoded = base64.b64encode(factories.build_zip()).decode()
    wrapped = "\n".join(encoded[i : i + 76] for i in range(0, len(encoded), 76))

    assert extract(write, payload=wrapped).zip_path is not None


def test_unknown_envelope_is_blocking(write) -> None:
    result = XmlZipExtractor().extract_zip(write("other.xml", b"<Other><csv>AAAA</csv></Other>"))

    assert codes(result.messages) == ["ENV-001"]
    assert result.zip_path is None


def test_several_declarations_are_blocking(write) -> None:
    assert codes(extract(write, declarations=2).messages) == ["ENV-002"]


def test_empty_or_invalid_payload_is_blocking(write) -> None:
    assert codes(extract(write, payload="  ").messages) == ["ENV-003"]
    assert codes(extract(write, payload="not base64 !!").messages) == ["ENV-004"]


def test_administration_block_is_checked_without_blocking(write) -> None:
    result = extract(write, sender="NOT-A-LEI", recipient="ECB", domain="XYZ", action=None)

    # Recipient and domain are kept for a later check (they depend on the competent authority).
    assert sorted(codes(result.messages)) == ["ENV-007", "ENV-008"]
    assert (result.recipient, result.domain) == ("ECB", "XYZ")
    assert result.valid and result.zip_path is not None


@pytest.mark.parametrize(
    ("authority", "expected"),
    [
        ("ACPR", True),
        ("acpr", True),
        ("Autorité de contrôle prudentiel et de résolution", True),
        ("Banque de France - ACPR", True),
        ("AMF", False),
        ("Autorité des marchés financiers", False),
        ("CSSF", False),
        ("", False),
        (None, False),
    ],
)
def test_competent_authority_is_recognised_as_acpr(authority, expected) -> None:
    assert is_acpr(authority) is expected


def test_onegate_target_is_checked_only_for_the_acpr() -> None:
    """PO decision (#14): ENV-005 and ENV-006 only when RT.01.01.0050 names the ACPR."""
    wrong = ("ECB", "XYZ")

    assert codes(check_onegate_target(*wrong, "ACPR")) == ["ENV-005", "ENV-006"]
    # Authority unreadable: the envelope is a OneGate one, so the rules apply.
    assert codes(check_onegate_target(*wrong, None)) == ["ENV-005", "ENV-006"]
    assert check_onegate_target(*wrong, "AMF") == []
    # Administration block not read: nothing to say.
    assert check_onegate_target(None, None, "ACPR") == []


@pytest.mark.parametrize("domain", ["DRB", "DRA"])
def test_banking_and_insurance_domains_are_both_accepted(domain) -> None:
    assert check_onegate_target("BDF", domain, "ACPR") == []
