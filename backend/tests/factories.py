# SPDX-License-Identifier: EUPL-1.2
"""Builds fictitious register packages and envelopes for the tests and samples.

Everything here is invented: the LEI is a dummy value and the column lists of
the templates are placeholders, not the official ones.
"""

import base64
import csv
import io
import json
import zipfile

from contracts import data_model, taxonomy
from contracts.naming import file_name_from_table_code

# Header the frontend sends with every request that changes something (review S6, 0.8.3).
CLIENT_HEADERS = {"X-ROI-Client": "tests"}

LEI = "DUMMYLEI123456789080"
# The minimal package lists providers without any arrangement: DQ-004 (INFO, provider used
# nowhere) is expected on it and only on it. It is not a business-complete register.
SYNTHETIC_ADMITTED = frozenset({"DQ-004"})
PACKAGE_NAME = f"{LEI}.CON_FR_DORA010100_DORA_2025-12-31_20260315120000000"
ENTRY_POINT = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/dora/4.0/mod/dora.json"
TEMPLATES = taxonomy.default_version().templates


def table_csv(code: str, *rows: dict[str, str]) -> bytes:
    """A table file with the real columns of the template and the given rows."""
    columns = data_model.tables()[code].columns
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    return out.getvalue().encode()


def default_files() -> dict[str, bytes]:
    """Files of a valid package, keyed by their path inside the package folder."""
    files: dict[str, bytes] = {
        "META-INF/reportPackage.json": json.dumps(
            {"documentInfo": {"documentType": "https://xbrl.org/report-package/2023"}}
        ).encode(),
        "reports/report.json": json.dumps(
            {
                "documentInfo": {
                    "documentType": "https://xbrl.org/2021/xbrl-csv",
                    "extends": [ENTRY_POINT],
                }
            }
        ).encode(),
        "reports/parameters.csv": (
            "name,value\n"
            f"entityID,rs:{LEI}.CON\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,iso4217:EUR\n"
            "decimalsInteger,0\n"
            "decimalsMonetary,-3\n"
        ).encode(),
        "reports/FilingIndicators.csv": (
            "templateID,reported\n" + "".join(f"{code},true\n" for code in TEMPLATES)
        ).encode(),
    }
    for code in TEMPLATES:
        files[f"reports/{file_name_from_table_code(code)}"] = table_csv(code)
    files["reports/b_01.01.csv"] = table_csv(
        "B_01.01",
        {
            "c0010": LEI,
            "c0020": "Entité fictive",
            "c0030": "eba_GA:FR",
            "c0040": "eba_CT:x12",
            # Competent authority: ACPR, so that OneGate envelope rules apply (#14).
            "c0050": "ACPR",
            "c0060": "2025-12-31",
        },
    )
    # The entity maintaining the register is also listed in B_01.02 (REL-001), as its own
    # ultimate parent (BUS-001, BUS-002).
    files["reports/b_01.02.csv"] = table_csv(
        "B_01.02",
        {
            "c0010": LEI,
            "c0020": "Entité fictive",
            "c0030": "eba_GA:FR",
            "c0040": "eba_CT:x12",
            "c0050": "eba_RP:x53",
            "c0060": LEI,
            "c0070": "2025-12-31",
            "c0080": "2025-01-01",
            "c0090": "9999-12-31",
            "c0100": "eba_CU:EUR",
            "c0110": "1000000",
        },
    )
    files["reports/b_05.01.csv"] = table_csv(
        "B_05.01",
        {
            "c0010": "FRRCSPARIS.552032534",
            "c0020": "eba_qCO:qx2002",
            "c0050": "Provider One",
            "c0060": "Provider One",
            "c0070": "eba_CT:x212",
            "c0080": "eba_GA:FR",
            "c0110": "FRRCSPARIS.552032534",
            "c0120": "eba_qCO:qx2002",
        },
        {
            "c0010": "IEIECRO.123456",
            "c0020": "eba_qCO:qx2002",
            "c0050": "Provider Two, Inc.",
            "c0060": "Provider Two, Inc.",
            "c0070": "eba_CT:x212",
            "c0080": "eba_GA:IE",
            "c0110": "FRRCSPARIS.552032534",
            "c0120": "eba_qCO:qx2002",
        },
    )
    return files


def build_zip(
    files: dict[str, bytes] | None = None,
    root: str | None = PACKAGE_NAME,
    extra: dict[str, bytes] | None = None,
) -> bytes:
    """Build a package archive. ``extra`` paths are relative to the archive root."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in (default_files() if files is None else files).items():
            archive.writestr(f"{root}/{path}" if root else path, content)
        for path, content in (extra or {}).items():
            archive.writestr(path, content)
    return buffer.getvalue()


def build_envelope(
    zip_bytes: bytes | None = None,
    sender: str = LEI,
    recipient: str = "BDF",
    domain: str = "DRB",
    action: str | None = "replace",
    declarations: int = 1,
    payload: str | None = None,
) -> bytes:
    """Build a OneGate envelope carrying a package encoded in base 64."""
    if payload is None:
        payload = base64.b64encode(zip_bytes if zip_bytes is not None else build_zip()).decode()
    action_attribute = f' action="{action}"' if action else ""
    declaration = (
        '<XbrlDeclarationReport xmlns="http://www.onegate.eu/2010-01-01">'
        "<Administration>"
        f'<From declarerType="LEI">{sender}</From>'
        f"<To>{recipient}</To>"
        f"<Domain>{domain}</Domain>"
        "<Response><Email>reporting@example.org</Email><Language>FR</Language></Response>"
        "</Administration>"
        f"<Report{action_attribute}><csv>{payload}</csv></Report>"
        "</XbrlDeclarationReport>"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<XbrlDelivery>"
        f"{declaration * declarations}"
        "</XbrlDelivery>"
    ).encode()
