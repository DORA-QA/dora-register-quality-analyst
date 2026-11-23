# SPDX-License-Identifier: EUPL-1.2
import pytest

from import_engine.file_type_detector import FileTypeDetector
from tests import factories


@pytest.mark.parametrize(
    ("name", "content", "expected"),
    [
        ("register.bin", factories.build_zip(), "ZIP"),
        ("register.txt", factories.build_envelope(), "XML"),
        ("bom.xml", b"\xef\xbb\xbf  <?xml version='1.0'?><a/>", "XML"),
        ("utf16.xml", "<?xml version='1.0'?><a/>".encode("utf-16"), "XML"),
        ("notes.zip", b"this is plain text", "UNKNOWN"),
        ("empty.xml", b"", "UNKNOWN"),
    ],
)
def test_type_is_detected_from_content_not_extension(write, name, content, expected) -> None:
    assert FileTypeDetector().detect(write(name, content)).detected_type == expected
