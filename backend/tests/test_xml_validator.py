# SPDX-License-Identifier: EUPL-1.2
from pathlib import Path

from contracts.messages import render_message
from import_engine.xml_validator import XmlValidator
from tests import factories
from tests.conftest import codes

XSD = b"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="a"><xs:complexType><xs:sequence>
    <xs:element name="b" type="xs:int"/>
  </xs:sequence></xs:complexType></xs:element>
</xs:schema>"""


def test_valid_envelope_without_xsd_is_silent(write) -> None:
    result = XmlValidator().validate(write("ok.xml", factories.build_envelope()))

    assert result.valid
    assert result.root_tag == "XbrlDelivery"
    assert result.messages == []
    assert not result.xsd_checked


def test_missing_closing_tag_is_blocking_and_located(write) -> None:
    result = XmlValidator().validate(write("ko.xml", b"<a><b></a>"))

    assert not result.valid
    assert codes(result.messages) == ["XML-002"]
    assert render_message(result.messages[0], "en").details.startswith("line 1, column")
    assert render_message(result.messages[0], "fr").details.startswith("ligne 1, colonne")


def test_invalid_encoding_is_blocking(write) -> None:
    content = b'<?xml version="1.0" encoding="UTF-8"?><a>\xe9t\xe9</a>'

    result = XmlValidator().validate(write("latin.xml", content))

    assert codes(result.messages) == ["XML-001"]


def test_doctype_is_refused(write) -> None:
    content = b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "y">]><a>&x;</a>'

    result = XmlValidator().validate(write("dtd.xml", content))

    assert codes(result.messages) == ["XML-003"]


def test_xsd_validation_with_one_or_several_schemas(write, tmp_path: Path) -> None:
    (tmp_path / "one.xsd").write_bytes(XSD)
    (tmp_path / "two.xsd").write_bytes(XSD)
    validator = XmlValidator.from_directory(tmp_path)

    valid = validator.validate(write("ok.xml", b"<a><b>1</b></a>"))
    invalid = validator.validate(write("ko.xml", b"<a><b>text</b></a>"))

    assert valid.xsd_checked and valid.messages == []
    assert codes(invalid.messages) == ["XML-004", "XML-004"]
    assert invalid.valid, "an XSD difference is a MAJOR, not a BLOCKER"
