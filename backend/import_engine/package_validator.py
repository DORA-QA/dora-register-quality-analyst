# SPDX-License-Identifier: EUPL-1.2
"""Structural validation of a register package before its tables are loaded."""

import csv
import io
import json
import re
import zipfile
import zlib
from pathlib import Path

from contracts import taxonomy
from contracts.dataset import PackageMetadata
from contracts.import_results import PackageValidationResult
from contracts.messages import ValidationMessage, fragment, make_message
from contracts.naming import file_name_from_table_code, table_code_from_file
from import_engine.package_layout import (
    FILING_INDICATORS,
    META_DIR,
    PARAMETERS,
    REPORT_JSON,
    REPORT_PACKAGE,
    REPORTS_DIR,
    REPORTS_FIXED_FILES,
    PackageLayout,
    read_layout,
)

PACKAGE_NAME = re.compile(
    r"^(?P<lei>[A-Z0-9]{20})\.(?P<scope>CON|IND)_(?P<country>[A-Z]{2})_(?P<module>[A-Z]+\d{6})"
    r"_(?P<framework>[A-Z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<timestamp>\d{14,17})$"
)
ENTITY_ID = re.compile(r"^rs:(?P<lei>[A-Z0-9]{20})\.(?P<scope>CON|IND)$")
ISO_DATE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
CURRENCY = re.compile(r"^iso4217:(?P<code>[A-Z]{3})$")
INTEGER = re.compile(r"^-?\d+$")
DECIMALS = re.compile(r"^(-?\d+|INF)$")  # filing rule 2.18: INF = exact value
MAX_DECIMALS_DIGITS = 18
REPORT_PACKAGE_TYPE = "https://xbrl.org/report-package/2023"
XBRL_CSV_TYPE = "https://xbrl.org/2021/xbrl-csv"
# Filing indicator values accepted by the EBA (xs:boolean without upper case).
# Lowest accepted monetary precision (EBA filing rule 2.18, from 01/04/2025).
MIN_MONETARY_DECIMALS = -4
FILING_TRUE = ("true", "1")
FILING_FALSE = ("false", "0")

# Parameter name -> (expected pattern, fragment describing the expected format).
PARAMETER_FORMATS = {
    "entityID": (ENTITY_ID, "expected_entity_id"),
    "refPeriod": (ISO_DATE, "expected_date"),
    "baseCurrency": (CURRENCY, "expected_currency"),
    "decimalsInteger": (DECIMALS, "expected_integer_0"),
    "decimalsMonetary": (DECIMALS, "expected_integer_m3"),
}


class PackageValidator:
    def validate(self, zip_file: str) -> PackageValidationResult:
        result = PackageValidationResult()
        try:
            archive = zipfile.ZipFile(zip_file)
        except (zipfile.BadZipFile, OSError, zlib.error):
            result.messages.append(make_message("ZIP-001"))
            return result

        with archive:
            layout = read_layout(archive)
            if layout.ignored:
                shown = ", ".join(layout.ignored[:5])
                result.messages.append(
                    make_message("PKG-024", count=str(len(layout.ignored)), files=shown)
                )
            if layout.footnotes:
                result.messages.append(make_message("PKG-026", file=layout.footnotes[0]))
            if layout.backslash_paths:
                shown = ", ".join(layout.backslash_paths[:5])
                result.messages.append(
                    make_message("PKG-025", count=str(len(layout.backslash_paths)), files=shown)
                )
            if layout.root is None:
                found = ", ".join(layout.root_entries[:5]) or fragment("nothing")
                result.messages.append(make_message("PKG-001", found=found))
                return result

            result.metadata.package_name = layout.root
            name_parts = self._check_name(layout.root, Path(zip_file).name, result)
            self._check_folders(layout, result)
            self._check_report_package(archive, layout, result)
            self._check_report_json(archive, layout, result)
            parameters = self._check_parameters(archive, layout, result)
            indicators = self._check_filing_indicators(archive, layout, result)
            self._check_templates(layout, indicators, result)
            self._check_consistency(name_parts, parameters, result)
        return result

    # ------------------------------------------------------------------ name
    @staticmethod
    def _check_name(
        root: str, zip_name: str, result: PackageValidationResult
    ) -> dict[str, str] | None:
        # An archive extracted from an envelope has no meaningful file name.
        if zip_name.lower().endswith(".zip") and zip_name != "package.zip":
            stem = zip_name[: -len(".zip")]
            if stem != root:
                result.messages.append(
                    make_message(
                        "PKG-002", details=fragment("folder_vs_zip", folder=root, zip=stem)
                    )
                )

        match = PACKAGE_NAME.match(root)
        if not match:
            result.messages.append(make_message("PKG-003", details=root))
            return None
        parts = match.groupdict()
        result.metadata.country = parts["country"]
        result.metadata.module_code = parts["module"]
        return parts

    # --------------------------------------------------------------- folders
    @staticmethod
    def _check_folders(layout: PackageLayout, result: PackageValidationResult) -> None:
        expected = {META_DIR, REPORTS_DIR}
        unexpected = sorted(set(layout.sub_folders) - expected)
        if unexpected:
            result.messages.append(make_message("PKG-004", found=", ".join(unexpected)))

        allowed_meta = {REPORT_PACKAGE}
        unexpected_files = list(layout.other_files)
        unexpected_files += [m for name, m in layout.meta_files.items() if name not in allowed_meta]
        unexpected_files += [
            member
            for name, member in layout.report_files.items()
            if name not in REPORTS_FIXED_FILES and table_code_from_file(name) is None
        ]
        for member in sorted(unexpected_files):
            result.messages.append(make_message("PKG-007", file=_inside(member, layout)))

        seen: dict[str, str] = {}
        for name in sorted(layout.report_files):
            key = name.lower()
            if key in seen:
                result.messages.append(make_message("PKG-008", file=f"{seen[key]}, {name}"))
            seen[key] = name

    # ------------------------------------------------------------ JSON files
    def _check_report_package(
        self, archive: zipfile.ZipFile, layout: PackageLayout, result: PackageValidationResult
    ) -> None:
        path = f"{META_DIR}/{REPORT_PACKAGE}"
        document = self._read_json(archive, layout.meta_files.get(REPORT_PACKAGE), path, result)
        if document is None:
            return
        if _document_type(document) != REPORT_PACKAGE_TYPE:
            reason = fragment("document_type", expected=REPORT_PACKAGE_TYPE)
            result.messages.append(make_message("PKG-006", file=path, reason=reason))

    def _check_report_json(
        self, archive: zipfile.ZipFile, layout: PackageLayout, result: PackageValidationResult
    ) -> None:
        path = f"{REPORTS_DIR}/{REPORT_JSON}"
        document = self._read_json(archive, layout.report_files.get(REPORT_JSON), path, result)
        if document is None:
            return
        if _document_type(document) != XBRL_CSV_TYPE:
            reason = fragment("document_type", expected=XBRL_CSV_TYPE)
            result.messages.append(make_message("PKG-006", file=path, reason=reason))

        info = document.get("documentInfo") if isinstance(document, dict) else None
        extends = info.get("extends") if isinstance(info, dict) else None
        if not (isinstance(extends, list) and len(extends) == 1 and isinstance(extends[0], str)):
            reason = fragment("extends_one")
            result.messages.append(make_message("PKG-006", file=path, reason=reason))
            return

        entry_point = extends[0]
        version = taxonomy.version_from_entry_point(entry_point)
        known = taxonomy.get_version(version) if version else None
        result.metadata.taxonomy_entry_point = entry_point
        result.metadata.taxonomy_version = version
        result.taxonomy_version = version
        if known is None or entry_point not in known.entry_points:
            supported = ", ".join(taxonomy.supported_versions())
            result.messages.append(make_message("PKG-009", value=entry_point, supported=supported))

    @staticmethod
    def _read_json(
        archive: zipfile.ZipFile,
        member: str | None,
        path: str,
        result: PackageValidationResult,
    ) -> object | None:
        if member is None:
            result.messages.append(make_message("PKG-005", file=path))
            return None
        try:
            return json.loads(archive.read(member).decode("utf-8-sig"))
        # ValueError covers a malformed document and a number past the digit limit of Python;
        # RecursionError a document nested too deeply (red team RT-20).
        except (UnicodeDecodeError, ValueError, RecursionError):
            result.messages.append(
                make_message("PKG-006", file=path, reason=fragment("json_invalid"))
            )
            return None

    # ------------------------------------------------------------ parameters
    def _check_parameters(
        self, archive: zipfile.ZipFile, layout: PackageLayout, result: PackageValidationResult
    ) -> dict[str, str]:
        path = f"{REPORTS_DIR}/{PARAMETERS}"
        rows = self._read_two_columns(
            archive, layout.report_files.get(PARAMETERS), path, ("name", "value"), result
        )
        if rows is None:
            return {}
        parameters = dict(rows)
        version = taxonomy.get_version(result.taxonomy_version or "") or taxonomy.default_version()

        for name in version.required_parameters:
            pattern, expected = PARAMETER_FORMATS[name]
            if not pattern.match(parameters.get(name, "")):
                result.messages.append(
                    make_message("PKG-014", name=name, expected=fragment(expected))
                )
        self._check_decimals(parameters, result)
        allowed = set(version.required_parameters) | set(version.optional_parameters)
        for name in sorted(set(parameters) - allowed):
            result.messages.append(make_message("PKG-015", name=name))

        entity = ENTITY_ID.match(parameters.get("entityID", ""))
        if entity:
            result.metadata.entity_lei = entity.group("lei")
            result.metadata.reporting_scope = entity.group("scope")
        if ISO_DATE.match(parameters.get("refPeriod", "")):
            result.metadata.reference_date = parameters["refPeriod"]
        currency = CURRENCY.match(parameters.get("baseCurrency", ""))
        if currency:
            result.metadata.base_currency = currency.group("code")
        return parameters

    @staticmethod
    def _check_decimals(parameters: dict[str, str], result: PackageValidationResult) -> None:
        """Accuracy requirements (EBA filing rule 2.18): monetary >= -4, integer = 0."""
        limits = (
            (
                "decimalsMonetary",
                lambda number: number >= MIN_MONETARY_DECIMALS,
                "decimals_monetary",
            ),
            ("decimalsInteger", lambda number: number == 0, "decimals_integer"),
        )
        for name, accepted, expected in limits:
            value = parameters.get(name, "")
            # Past MAX_DECIMALS_DIGITS digits the value is refused without being read: Python
            # does not convert more than 4,300 digits (red team RT-20).
            if INTEGER.match(value) and (
                len(value.lstrip("-")) > MAX_DECIMALS_DIGITS or not accepted(int(value))
            ):
                result.messages.append(
                    make_message("PKG-023", name=name, value=value, expected=fragment(expected))
                )

    # ----------------------------------------------------- filing indicators
    def _check_filing_indicators(
        self, archive: zipfile.ZipFile, layout: PackageLayout, result: PackageValidationResult
    ) -> dict[str, str]:
        path = f"{REPORTS_DIR}/{FILING_INDICATORS}"
        rows = self._read_two_columns(
            archive,
            layout.report_files.get(FILING_INDICATORS),
            path,
            ("templateID", "reported"),
            result,
        )
        return dict(rows) if rows is not None else {}

    @staticmethod
    def _check_templates(
        layout: PackageLayout, indicators: dict[str, str], result: PackageValidationResult
    ) -> None:
        version = taxonomy.get_version(result.taxonomy_version or "") or taxonomy.default_version()
        present = layout.table_members()
        has_indicators = FILING_INDICATORS in layout.report_files

        for name in sorted(layout.report_files):
            if table_code_from_file(name) is not None and name != name.lower():
                result.messages.append(make_message("PKG-018", file=name))

        result.rt_detected = sorted(present)
        for template in version.templates:
            file_name = file_name_from_table_code(template)
            if template not in present:
                result.missing_rt.append(template)
                result.messages.append(make_message("PKG-010", template=template, file=file_name))
            if not has_indicators:
                continue
            value = indicators.get(template)
            if value is None:
                result.messages.append(make_message("PKG-011", template=template))
            elif value not in FILING_TRUE + FILING_FALSE:
                result.messages.append(make_message("PKG-013", template=template, value=value))
            else:
                if value in ("1", "0"):
                    result.messages.append(make_message("PKG-022", template=template, value=value))
                if value in FILING_FALSE and template in present:
                    result.messages.append(
                        make_message("PKG-012", template=template, file=file_name)
                    )

        for template in sorted(set(indicators) - set(version.templates)):
            result.messages.append(make_message("PKG-020", template=template))
        for template in sorted(set(present) - set(version.templates)):
            result.messages.append(
                make_message("PKG-007", file=_inside(present[template][1], layout))
            )

    # ----------------------------------------------------------- consistency
    @staticmethod
    def _check_consistency(
        name_parts: dict[str, str] | None,
        parameters: dict[str, str],
        result: PackageValidationResult,
    ) -> None:
        if name_parts is None:
            return
        metadata = result.metadata
        if metadata.entity_lei and name_parts["lei"] != metadata.entity_lei:
            result.messages.append(make_message("PKG-016"))
        if metadata.reporting_scope and name_parts["scope"] != metadata.reporting_scope:
            result.messages.append(
                make_message(
                    "PKG-021",
                    name_scope=name_parts["scope"],
                    param_scope=metadata.reporting_scope,
                )
            )
        if metadata.reference_date and name_parts["date"] != metadata.reference_date:
            result.messages.append(make_message("PKG-017"))

        version = taxonomy.get_version(result.taxonomy_version or "")
        if version and name_parts["module"] != version.module_code:
            result.messages.append(
                make_message(
                    "PKG-019",
                    value=name_parts["module"],
                    version=version.version,
                    expected=version.module_code,
                )
            )

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _read_two_columns(
        archive: zipfile.ZipFile,
        member: str | None,
        path: str,
        header: tuple[str, str],
        result: PackageValidationResult,
    ) -> list[tuple[str, str]] | None:
        """Read a small two-column CSV file of the package (parameters, indicators)."""
        if member is None:
            result.messages.append(make_message("PKG-005", file=path))
            return None
        try:
            text = archive.read(member).decode("utf-8-sig")
        except UnicodeDecodeError:
            result.messages.append(make_message("CSV-001", file=path))
            return None

        rows = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
        if not rows or tuple(rows[0]) != header:
            reason = fragment("first_line", header=f"{header[0]},{header[1]}")
            result.messages.append(make_message("PKG-006", file=path, reason=reason))
            return None
        if any(len(row) != 2 for row in rows[1:]):
            reason = fragment("two_values")
            result.messages.append(make_message("PKG-006", file=path, reason=reason))
            return None
        return [(row[0], row[1]) for row in rows[1:]]


def _inside(member: str, layout: PackageLayout) -> str:
    """Path of a member relative to the package folder, easier to read in a message."""
    prefix = f"{layout.root}/"
    return member[len(prefix) :] if member.startswith(prefix) else member


def _document_type(document: object) -> str | None:
    if not isinstance(document, dict):
        return None
    info = document.get("documentInfo")
    return info.get("documentType") if isinstance(info, dict) else None


def cross_check_envelope(
    sender_lei: str | None, metadata: PackageMetadata
) -> list[ValidationMessage]:
    """Compare the sender of an envelope with the entity of the package."""
    if sender_lei and metadata.entity_lei and sender_lei != metadata.entity_lei:
        return [make_message("ENV-009")]
    return []
