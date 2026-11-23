# SPDX-License-Identifier: EUPL-1.2
"""Detects whether a file is an XML document or a ZIP archive, from its content."""

from pathlib import Path

from contracts.import_results import (
    FILE_TYPE_UNKNOWN,
    FILE_TYPE_XML,
    FILE_TYPE_ZIP,
    FileTypeResult,
)

ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
BOMS = (
    (b"\xef\xbb\xbf", "utf-8"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)
SNIFF_SIZE = 512


class FileTypeDetector:
    """The file extension is ignored: users rename files, content does not lie."""

    def detect(self, file_path: str) -> FileTypeResult:
        with Path(file_path).open("rb") as handle:
            head = handle.read(SNIFF_SIZE)

        if head.startswith(ZIP_SIGNATURES):
            return FileTypeResult(FILE_TYPE_ZIP)
        if self._looks_like_xml(head):
            return FileTypeResult(FILE_TYPE_XML)
        return FileTypeResult(FILE_TYPE_UNKNOWN)

    @staticmethod
    def _looks_like_xml(head: bytes) -> bool:
        encoding = "utf-8"
        for bom, bom_encoding in BOMS:
            if head.startswith(bom):
                head, encoding = head[len(bom) :], bom_encoding
                break
        text = head.decode(encoding, errors="ignore").lstrip()
        return text.startswith("<")
