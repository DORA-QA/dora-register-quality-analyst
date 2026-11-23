# SPDX-License-Identifier: EUPL-1.2
"""Generic validation of an XML file: readable, well-formed, safe, XSD-valid.

Nothing here is specific to a given envelope: the checks that depend on the
OneGate format live in ``onegate.py``.
"""

from pathlib import Path

from lxml import etree

from contracts.import_results import XmlValidationResult
from contracts.messages import ValidationMessage, fragment, make_message

MAX_XSD_ERRORS = 10


def secure_parser_options() -> dict:
    """Options shared by every XML parser of the product.

    No DTD loading, no entity expansion, no network access. ``huge_tree`` is
    required because the package is carried as one very long text node.
    """
    return {
        "resolve_entities": False,
        "load_dtd": False,
        "no_network": True,
        "huge_tree": True,
    }


class XmlValidator:
    """Validates an XML file against zero, one or several XSD schemas."""

    def __init__(self, xsd_paths: list[Path] | None = None) -> None:
        self._xsd_paths = sorted(xsd_paths or [])

    @classmethod
    def from_directory(cls, directory: Path) -> "XmlValidator":
        """Use every ``.xsd`` file found in a directory."""
        return cls(list(directory.glob("*.xsd")) if directory.is_dir() else [])

    def validate(self, xml_file: str) -> XmlValidationResult:
        result = XmlValidationResult()

        root_tag, parse_error = self._check_well_formed(xml_file)
        if parse_error is not None:
            result.messages.append(parse_error)
            return result
        result.root_tag = root_tag

        # No XSD exists for the OneGate envelope: the product's own controls apply.
        if not self._xsd_paths:
            return result

        result.messages.extend(self._check_schemas(xml_file))
        result.xsd_checked = True
        return result

    @staticmethod
    def _check_well_formed(xml_file: str) -> tuple[str | None, ValidationMessage | None]:
        """Stream the file once. Elements are released as soon as they are closed."""
        root_tag: str | None = None
        try:
            context = etree.iterparse(xml_file, events=("start", "end"), **secure_parser_options())
            for event, element in context:
                if event == "start":
                    if root_tag is None:
                        root_tag = etree.QName(element).localname
                        if element.getroottree().docinfo.doctype:
                            return None, make_message("XML-003")
                else:
                    element.clear()
        except etree.XMLSyntaxError as error:
            line, column = error.position
            details = fragment("xml_position", line=line, column=column, parser=error.msg)
            code = "XML-001" if _is_encoding_error(error) else "XML-002"
            return None, make_message(code, details=details)
        except (OSError, UnicodeError, LookupError) as error:
            return None, make_message("XML-001", details=type(error).__name__)
        return root_tag, None

    def _check_schemas(self, xml_file: str) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        document = etree.parse(xml_file, etree.XMLParser(**secure_parser_options()))
        for xsd_path in self._xsd_paths:
            schema = etree.XMLSchema(etree.parse(str(xsd_path)))
            if schema.validate(document):
                continue
            errors = [f"{e.line}: {e.message}" for e in schema.error_log][:MAX_XSD_ERRORS]
            messages.append(
                make_message("XML-004", details=f"{xsd_path.name}\n" + "\n".join(errors))
            )
        return messages


def _is_encoding_error(error: etree.XMLSyntaxError) -> bool:
    message = (error.msg or "").lower()
    return "encoding" in message or "not proper utf-8" in message
