# SPDX-License-Identifier: EUPL-1.2
import io
import zipfile

from import_engine.zip_validator import ZipValidator
from tests import factories
from tests.conftest import codes


def test_valid_archive_gives_count_size_and_inventory(valid_zip) -> None:
    result = ZipValidator().validate(valid_zip)

    assert result.valid and result.messages == []
    assert result.file_count == 19
    assert result.package_size > 0
    assert f"{factories.PACKAGE_NAME}/reports/b_01.01.csv" in result.inventory


def test_unreadable_archive(write) -> None:
    truncated = factories.build_zip()[:200]

    assert codes(ZipValidator().validate(write("ko.zip", truncated)).messages) == ["ZIP-001"]


def test_corrupted_member(write) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("pkg/reports/b_01.01.csv", b"c0010\n" + b"A" * 5000)
    data = bytearray(buffer.getvalue())
    data[data.find(b"AAAA") + 100] ^= 0xFF

    result = ZipValidator().validate(write("ko.zip", bytes(data)))

    assert codes(result.messages) == ["ZIP-002"]


def test_empty_archive(write) -> None:
    assert codes(ZipValidator().validate(write("e.zip", factories.build_zip({}))).messages) == [
        "ZIP-008"
    ]


def test_limits_on_entries_and_size(write) -> None:
    files = {f"reports/f{i}.csv": b"x" * 1024 for i in range(30)}
    path = write("big.zip", factories.build_zip(files))

    assert codes(ZipValidator(max_files=10).validate(path).messages) == ["ZIP-004"]
    assert codes(ZipValidator(max_uncompressed_mb=0).validate(path).messages) == ["ZIP-005"]


def test_unsafe_path_and_nested_archive(write) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../evil.csv", b"x")
        archive.writestr("pkg/reports/inner.zip", b"x")

    result = ZipValidator().validate(write("unsafe.zip", buffer.getvalue()))

    assert sorted(codes(result.messages)) == ["ZIP-006", "ZIP-007"]


# ------------------------------------------------- red team du 07/11 (RT-23, RT-24, CL-47)
def _archive(*names: str) -> bytes:
    import warnings

    buffer = io.BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(buffer, "w") as archive:
        warnings.simplefilter("ignore")
        for name in names:
            archive.writestr(name, b"x")
    return buffer.getvalue()


def test_two_members_with_the_same_name_are_reported(write) -> None:
    data = _archive("pkg/reports/b_01.01.csv", "pkg/reports/b_01.01.csv", "pkg/a.csv")
    result = ZipValidator().validate(write("dup.zip", data))
    assert codes(result.messages) == ["ZIP-009"]
    assert result.messages[0].params["files"] == "pkg/reports/b_01.01.csv"


def test_a_name_hidden_after_a_nul_byte_is_reported(write) -> None:
    # zipfile cuts the name at the NUL byte: "pkg/a.csv" would hide "../../evil". zipfile cannot
    # write such a name, so the byte is put in place in the archive.
    data = _archive("pkg/a.csv#/../../evil").replace(b"a.csv#", b"a.csv\x00")
    result = ZipValidator().validate(write("nul.zip", data))
    assert codes(result.messages) == ["ZIP-006"]
    assert result.messages[0].params["file"] == "pkg/a.csv\\u0000/../../evil"


def test_a_right_to_left_override_in_a_name_is_reported(write) -> None:
    result = ZipValidator().validate(write("rtl.zip", _archive("pkg/reports/b_01‮csv.zip")))
    assert "ZIP-006" in codes(result.messages)
    shown = [m.params["file"] for m in result.messages if m.code == "ZIP-006"]
    assert shown == ["pkg/reports/b_01\\u202ecsv.zip"]
