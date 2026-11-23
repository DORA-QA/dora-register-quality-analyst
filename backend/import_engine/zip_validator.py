# SPDX-License-Identifier: EUPL-1.2
"""Technical validation of a ZIP archive: readable, intact and safe to open."""

import unicodedata
import zipfile
import zlib
from collections import Counter
from pathlib import PurePosixPath

from contracts.import_results import ZipValidationResult
from contracts.messages import make_message

ARCHIVE_EXTENSIONS = (".zip", ".7z", ".rar", ".gz", ".tar")
ENCRYPTED_FLAG = 0x1
MEGABYTE = 1024 * 1024


class ZipValidator:
    def __init__(self, max_files: int = 200, max_uncompressed_mb: int = 500) -> None:
        self._max_files = max_files
        self._max_uncompressed_mb = max_uncompressed_mb

    def validate(self, zip_file: str) -> ZipValidationResult:
        result = ZipValidationResult()
        try:
            archive = zipfile.ZipFile(zip_file)
        except (zipfile.BadZipFile, OSError):
            result.messages.append(make_message("ZIP-001"))
            return result

        with archive:
            entries = archive.infolist()
            files = [entry for entry in entries if not entry.is_dir()]
            result.file_count = len(files)
            result.package_size = sum(entry.file_size for entry in files)
            result.inventory = sorted(entry.filename for entry in files)

            if not files:
                result.messages.append(make_message("ZIP-008"))
                return result
            if len(entries) > self._max_files:
                result.messages.append(
                    make_message("ZIP-004", count=len(entries), limit=self._max_files)
                )
                return result
            if result.package_size > self._max_uncompressed_mb * MEGABYTE:
                result.messages.append(make_message("ZIP-005", limit=self._max_uncompressed_mb))
                return result

            for entry in entries:
                # ``orig_filename``: zipfile cuts a name at its first NUL byte, which would hide
                # the rest of it (red team RT-24).
                name = entry.orig_filename
                if _is_unsafe_path(name) or _has_control_character(name):
                    result.messages.append(make_message("ZIP-006", file=shown_name(name)))
            # Two members with the same name: the engine reads one, another tool may read the
            # other (red team RT-23).
            seen = Counter(entry.filename.replace("\\", "/") for entry in entries)
            repeated = sorted(name for name, count in seen.items() if count > 1)
            if repeated:
                result.messages.append(
                    make_message("ZIP-009", files=", ".join(shown_name(name) for name in repeated))
                )
            if any(entry.flag_bits & ENCRYPTED_FLAG for entry in files):
                result.messages.append(make_message("ZIP-003"))
                return result
            for entry in files:
                if entry.filename.lower().endswith(ARCHIVE_EXTENSIONS):
                    result.messages.append(make_message("ZIP-007", file=entry.filename))

            try:
                corrupted = archive.testzip()
            except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, zlib.error):
                corrupted = "?"
            if corrupted is not None:
                result.messages.append(make_message("ZIP-002", file=corrupted))
        return result


def _is_unsafe_path(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return path.is_absolute() or ".." in path.parts or ":" in path.parts[0] if path.parts else True


def _has_control_character(name: str) -> bool:
    """NUL and other control characters, and invisible formatting ones such as the
    right-to-left override, which can make a name look like another (red team RT-24)."""
    return any(unicodedata.category(char) in {"Cc", "Cf"} for char in name)


def shown_name(name: str) -> str:
    """The name with its control and formatting characters written as escapes (``\\u202e``)."""
    return "".join(
        f"\\u{ord(char):04x}" if unicodedata.category(char) in {"Cc", "Cf"} else char
        for char in name
    )
