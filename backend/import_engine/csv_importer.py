# SPDX-License-Identifier: EUPL-1.2
"""Loads the template files of a package into Polars tables.

Every column is read as text, with no type conversion: the rules of the next
sprints must see the raw value exactly as it was reported.
"""

import csv
import io
import re
import zipfile
import zlib
from collections import Counter

import polars as pl

from contracts.import_results import CsvImportResult, TableSummary
from contracts.messages import make_message
from import_engine.package_layout import REPORTS_DIR, read_layout

UTF8_BOM = b"\xef\xbb\xbf"
ROW_COLUMN = "_row"
CHUNK = 1 << 20  # bytes decompressed at a time to count the rows

# Import limits decided by the PO on 07/11/2026 (CL-46, red team RT-21). They keep a file far from
# any real register from exhausting the memory of the machine (3 GB in the Docker stack).
# A cell: the EBA data model allows 255 characters at most in a text field.
MAX_CELL_CHARACTERS = 10_000
# A table: the widest table of the model has 19 columns.
MAX_COLUMNS = 200
# The register: data rows of all the tables (3.5 million measured at 2.2 GB, 30/10/2026).
MAX_ROWS = 2_000_000

# A carriage return that does not start a CR+LF pair (CSV-012).
BARE_CR = re.compile(rb"\r(?!\n)")


def _count_rows(archive: zipfile.ZipFile, member: str, allowed: int) -> int:
    """Data rows of a file, counted on the raw lines while it is decompressed.

    The count stops as soon as it passes ``allowed``: a file of millions of rows is refused
    before it is read whole (red team RT-21). A line break inside a quoted cell counts as a row,
    a last line without a line break does not (one row per table at most).
    """
    lines = 0
    with archive.open(member) as stream:
        while chunk := stream.read(CHUNK):
            lines += chunk.count(b"\n")
            if lines - 1 > allowed:
                break
    return max(0, lines - 1)


class CsvImporter:
    def __init__(
        self,
        max_cell_characters: int = MAX_CELL_CHARACTERS,
        max_columns: int = MAX_COLUMNS,
        max_rows: int = MAX_ROWS,
    ) -> None:
        self._max_cell_characters = max_cell_characters
        self._max_columns = max_columns
        self._max_rows = max_rows

    def load(self, zip_file: str) -> CsvImportResult:
        result = CsvImportResult()
        try:
            archive = zipfile.ZipFile(zip_file)
        except (zipfile.BadZipFile, OSError, zlib.error):
            result.messages.append(make_message("ZIP-001"))
            return result

        with archive:
            tables = read_layout(archive).table_members()
            rows = 0
            for code, (file_name, member) in tables.items():
                path = f"{REPORTS_DIR}/{file_name}"
                rows += _count_rows(archive, member, self._max_rows - rows)
                if rows > self._max_rows:
                    # Nothing is analysed: a partial register would give misleading findings.
                    result.tables.clear()
                    result.summaries.clear()
                    result.messages.append(make_message("CSV-010", file=path, limit=self._max_rows))
                    return result
                frame = self._load_table(archive.read(member), path, result)
                if frame is None:
                    continue
                result.tables[code] = frame
                result.summaries.append(
                    TableSummary(
                        code=code, file=file_name, rows=frame.height, columns=frame.width - 1
                    )
                )
        return result

    def _load_table(
        self, content: bytes, path: str, result: CsvImportResult
    ) -> pl.DataFrame | None:
        if content.startswith(UTF8_BOM):
            result.messages.append(make_message("CSV-002", file=path))
            content = content[len(UTF8_BOM) :]
        # Before the file is decoded whole: a cell of 300 MB is stopped as soon as it passes
        # the limit (red team RT-21).
        line = self._huge_cell_line(content)
        if line is not None:
            result.messages.append(
                make_message("CSV-008", file=path, line=line, limit=self._max_cell_characters)
            )
            return None
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            result.messages.append(make_message("CSV-001", file=path))
            return None
        _check_line_endings(content, path, result)

        first_line = text.split("\n", 1)[0].strip()
        if not first_line:
            result.messages.append(make_message("CSV-003", file=path))
            return None
        try:
            header = next(csv.reader([first_line]))
        except csv.Error:
            # A stray carriage return inside the header row: the file cannot be parsed.
            result.messages.append(make_message("CSV-004", file=path))
            return None
        if len(header) == 1 and ";" in first_line:
            result.messages.append(make_message("CSV-005", file=path))
            return None
        names = [name.strip() for name in header]
        if len(names) > self._max_columns:
            result.messages.append(
                make_message("CSV-009", file=path, count=len(names), limit=self._max_columns)
            )
            return None
        # Rule 801 (ACPR, EBA): an unnamed column (CSV-006) and a repeated name (CSV-007)
        # are told apart so the reader knows what to fix (PO, #109).
        if any(not name for name in names):
            result.messages.append(make_message("CSV-006", file=path))
            return None
        # Counted in one pass: ``names.count`` for every name was quadratic (red team RT-17).
        repeated = sorted(name for name, seen in Counter(names).items() if seen > 1)
        if repeated:
            result.messages.append(make_message("CSV-007", file=path, columns=", ".join(repeated)))
            return None

        del text
        try:
            frame = pl.read_csv(
                io.BytesIO(content),
                has_header=True,
                infer_schema=False,
                encoding="utf8",
                truncate_ragged_lines=False,
            )
        except (pl.exceptions.ComputeError, pl.exceptions.NoDataError, pl.exceptions.ShapeError):
            result.messages.append(make_message("CSV-004", file=path))
            return None
        return frame.rename(lambda name: name.strip()).with_row_index(ROW_COLUMN, offset=1)

    def _huge_cell_line(self, content: bytes) -> int | None:
        """Line of the file where a cell passes the limit, None when every cell is within it.

        The file is read by the csv module with its field size limit, decoded piece by piece: a
        cell of 300 MB is stopped as soon as it passes the limit, without being loaded.
        A quoted cell spread over several lines is measured whole.
        """
        previous = csv.field_size_limit(self._max_cell_characters)
        lines = io.TextIOWrapper(io.BytesIO(content), encoding="utf-8", newline="")
        reader = csv.reader(lines)
        try:
            for _ in reader:
                pass
        except csv.Error as error:
            if "field larger than field limit" in str(error):
                return reader.line_num
            # Any other fault of the file is reported by Polars (CSV-004).
        except UnicodeDecodeError:
            pass  # reported just after (CSV-001)
        finally:
            csv.field_size_limit(previous)
        return None


def _check_line_endings(content: bytes, path: str, result: CsvImportResult) -> None:
    """Every line ends with LF or CR+LF, the last one included.

    ECB check on all xBRL-CSV submissions since 02/10/2026 (eSurfi, 20/10/2026); the EBA
    accepts a last line without a line break (S12 p. 25). Decision of the PO (09/11/2026):
    MAJOR, the file is still loaded. A line break inside a quoted cell is cell content and is
    not checked. The file is read in one pass: an old Mac file of a million lines (CR only)
    stays linear.
    """
    if not content:
        return
    first_line = 0
    count = 0
    quotes = 0
    lines = 1
    start = 0
    for match in BARE_CR.finditer(content):
        position = match.start()
        quotes += content.count(b'"', start, position)
        lines += content.count(b"\n", start, position)
        start = position
        if quotes % 2:
            continue  # inside a quoted cell
        count += 1
        if not first_line:
            first_line = lines
        lines += 1
    if count:
        result.messages.append(make_message("CSV-012", file=path, line=first_line, count=count))
    elif not content.endswith(b"\n"):
        result.messages.append(
            make_message("CSV-011", file=path, line=lines + content.count(b"\n", start))
        )
