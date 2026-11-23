# SPDX-License-Identifier: EUPL-1.2
"""Reads the layout of a package inside a ZIP archive.

Expected layout (EBA, plain-csv package of the DORA module)::

    {package name}/
        META-INF/reportPackage.json
        reports/report.json
        reports/parameters.csv
        reports/FilingIndicators.csv
        reports/b_01.01.csv ... b_99.01.csv
"""

import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from contracts.naming import table_code_from_file

META_DIR = "META-INF"
REPORTS_DIR = "reports"
REPORT_PACKAGE = "reportPackage.json"
REPORT_JSON = "report.json"
PARAMETERS = "parameters.csv"
FILING_INDICATORS = "FilingIndicators.csv"
# XBRL file the EBA expects and ignores (EBA S12 p. 24); accepted and left out (PO-30, #100).
FOOTNOTES = "FootNotes.csv"
REPORTS_FIXED_FILES = (REPORT_JSON, PARAMETERS, FILING_INDICATORS)


@dataclass
class PackageLayout:
    """Where things are in the archive. Paths are archive member names."""

    root_entries: list[str] = field(default_factory=list)  # names at the top of the archive
    root: str | None = None  # the single root folder, when there is exactly one
    sub_folders: list[str] = field(default_factory=list)
    meta_files: dict[str, str] = field(default_factory=dict)  # file name -> member
    report_files: dict[str, str] = field(default_factory=dict)  # file name -> member
    other_files: list[str] = field(default_factory=list)  # files outside the two folders
    ignored: list[str] = field(default_factory=list)  # macOS metadata, left out of the analysis
    backslash_paths: list[str] = field(default_factory=list)  # members written with "\\"
    footnotes: list[str] = field(default_factory=list)  # reports/FootNotes.csv, ignored (PO-30)

    def table_members(self) -> dict[str, tuple[str, str]]:
        """Map table code -> (file name, member) for every template file found."""
        tables: dict[str, tuple[str, str]] = {}
        for name, member in sorted(self.report_files.items()):
            code = table_code_from_file(name)
            if code is not None and code not in tables:
                tables[code] = (name, member)
        return tables


def is_macos_metadata(path: PurePosixPath) -> bool:
    """__MACOSX/ folders, AppleDouble files (._*) and .DS_Store, added by Finder when zipping."""
    return "__MACOSX" in path.parts or path.name.startswith("._") or path.name == ".DS_Store"


def read_layout(archive: zipfile.ZipFile) -> PackageLayout:
    layout = PackageLayout()
    files = []
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        if is_macos_metadata(PurePosixPath(entry.filename.replace("\\", "/"))):
            layout.ignored.append(entry.filename)
        else:
            files.append(entry.filename)
            if "\\" in entry.filename:
                layout.backslash_paths.append(entry.filename)
    paths = [PurePosixPath(name.replace("\\", "/")) for name in files]

    layout.root_entries = sorted({path.parts[0] for path in paths if path.parts})
    has_root_files = any(len(path.parts) == 1 for path in paths)
    if len(layout.root_entries) != 1 or has_root_files:
        return layout

    layout.root = layout.root_entries[0]
    sub_folders: set[str] = set()
    for name, path in zip(files, paths, strict=True):
        inner = path.parts[1:]
        if len(inner) == 1:
            layout.other_files.append(name)
            continue
        sub_folders.add(inner[0])
        if len(inner) == 2 and inner[0] == META_DIR:
            layout.meta_files[inner[1]] = name
        elif len(inner) == 2 and inner[0] == REPORTS_DIR:
            if inner[1] == FOOTNOTES:
                layout.footnotes.append(name)
            else:
                layout.report_files[inner[1]] = name
        else:
            layout.other_files.append(name)
    layout.sub_folders = sorted(sub_folders)
    return layout
