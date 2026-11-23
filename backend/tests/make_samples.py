# SPDX-License-Identifier: EUPL-1.2
"""Writes fictitious sample files to ``sample-data/``.

Run from ``backend/`` with::

    uv run python -m tests.make_samples
"""

from pathlib import Path

from tests import factories
from tests.cases.golden import load_golden
from tests.cases.mutations import MUTATIONS

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample-data"


def invalid_files() -> dict[str, bytes]:
    """A package with typical defects: missing template, extra file, BOM, wrong indicator."""
    files = factories.default_files()
    del files["reports/b_99.01.csv"]
    files["reports/register.xlsx"] = b"not a real workbook"
    files["reports/b_02.01.csv"] = b"\xef\xbb\xbfc0010,c0020\nCA-001,eba_CO:x1\n"
    files["reports/b_03.01.csv"] = b"c0010;c0020\nCA-001;X\n"
    files["reports/FilingIndicators.csv"] = files["reports/FilingIndicators.csv"].replace(
        b"B_01.03,true", b"B_01.03,TRUE"
    )
    return files


def data_defect_files() -> dict[str, bytes]:
    """A package that is well formed but whose data breaks the technical rules on keys."""
    files = factories.default_files()
    entity = {"c0010": factories.LEI, "c0020": "Entité fictive"}
    files["reports/b_01.02.csv"] = factories.table_csv(
        "B_01.02", entity, entity, {"c0010": "", "c0020": "Sans clé"}
    )
    files["reports/b_05.01.csv"] = factories.table_csv(
        "B_05.01",
        {"c0010": "DEK1101R.HRB116737", "c0020": "eba_qCO:qx2002"},
        {"c0010": "116737", "c0020": "eba_qCO:qx2002"},
        {"c0010": "USDE.12345", "c0020": "eba_qCO:qx2002"},
        {"c0010": "5493001KJTIIGC8Y1R13", "c0020": "eba_qCO:qx2000"},
    )
    files["reports/b_02.01.csv"] = factories.table_csv("B_02.01", {"c0010": "CA-001"})
    files["reports/b_03.01.csv"] = factories.table_csv(
        "B_03.01",
        {"c0010": "CA-001", "c0020": factories.LEI},
        {"c0010": "CA-404", "c0020": factories.LEI},
    )
    header, row = (
        factories.table_csv("B_06.01", {"c0010": "F-1", "c0040": factories.LEI})
        .decode()
        .splitlines()
    )
    files["reports/b_06.01.csv"] = f"{header},c0999\n{row},x\n".encode()
    return files


# Sprint 3 (brief §16.3): one defect per family of controls, applied together to the golden.
MULTI_DEFECT_CASES = (
    "M-REL-004",  # lot 1, entités
    "M-DQ-001",  # lot 2, prestataires
    "M-BUS-009",  # lot 3, accords
    "M-REL-012",  # lot 4, fonctions (BLOCKER provisoire)
    "M-REL-016",  # lot 4, services des fonctions critiques
    "M-REL-019",  # lot 5, chaînes
    "M-BUS-019",  # lot 5, identifiant en chaîne critique
    "M-DAT-033",  # lot 6, listes fermées (libellé)
    "M-DAT-033-HRK",  # lot 6, listes fermées (devise HRK)
)
MULTI_DEFECT_NAME = "package-multi-defects.sample.zip"


def multi_defect_package() -> bytes:
    """The golden with every case of ``MULTI_DEFECT_CASES``; expected findings in the manifest."""
    by_case = {mutation.case: mutation for mutation in MUTATIONS}
    package = load_golden()
    content = b""
    for case in MULTI_DEFECT_CASES:
        _, content = by_case[case].apply(package)
    return content


def main() -> None:
    SAMPLE_DIR.mkdir(exist_ok=True)
    samples = {
        f"{factories.PACKAGE_NAME}.zip": factories.build_zip(),
        "onegate-envelope-valid.sample.xml": factories.build_envelope(),
        "package-with-defects.sample.zip": factories.build_zip(invalid_files()),
        "package-with-data-defects.sample.zip": factories.build_zip(data_defect_files()),
        "onegate-envelope-with-defects.sample.xml": factories.build_envelope(
            factories.build_zip(invalid_files()), sender="OTHERLEI000000000099", domain="XYZ"
        ),
        MULTI_DEFECT_NAME: multi_defect_package(),
    }
    for name, content in samples.items():
        (SAMPLE_DIR / name).write_bytes(content)
        print(f"{name}: {len(content)} bytes")


if __name__ == "__main__":
    main()
