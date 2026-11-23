# SPDX-License-Identifier: EUPL-1.2
"""Extracts the ZIP package carried by an XML envelope.

The extractor knows nothing about a given envelope: it asks each registered
strategy whether it recognises the root element. Supporting another authority
means writing a strategy and adding it to the list.
"""

from pathlib import Path
from typing import Protocol

from lxml import etree

from contracts.import_results import ExtractedZip
from contracts.messages import make_message
from import_engine.onegate import OneGateExtractionStrategy
from import_engine.xml_validator import secure_parser_options


class ExtractionStrategy(Protocol):
    name: str

    def matches(self, root_tag: str) -> bool: ...

    def extract(self, xml_file: str, output_dir: Path) -> ExtractedZip: ...


def default_strategies() -> list[ExtractionStrategy]:
    return [OneGateExtractionStrategy()]


class XmlZipExtractor:
    def __init__(self, strategies: list[ExtractionStrategy] | None = None) -> None:
        self._strategies = strategies if strategies is not None else default_strategies()

    def extract_zip(self, xml_file: str) -> ExtractedZip:
        """Write the package next to the XML file and return its path."""
        root_tag = _read_root_tag(xml_file)
        for strategy in self._strategies:
            if strategy.matches(root_tag):
                return strategy.extract(xml_file, Path(xml_file).parent)
        return ExtractedZip(messages=[make_message("ENV-001", root=root_tag)])


def _read_root_tag(xml_file: str) -> str:
    context = etree.iterparse(xml_file, events=("start",), **secure_parser_options())
    _, root = next(context)
    return etree.QName(root).localname
