# SPDX-License-Identifier: EUPL-1.2
"""Le package « golden » : un seul fichier conforme dont les cas de test sont dérivés par mutation.

Si ``tests/golden/golden.zip`` (local) ou ``golden.sample.zip`` (anonymisé, versionné)
existe, il est utilisé.
Sinon on retombe sur le package synthétique de ``tests/factories.py``.
"""

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from tests import factories

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden"
# golden.zip : local, jamais versionné (données réelles possibles).
# golden.sample.zip : anonymisé, versionné.
GOLDEN_FILES = (GOLDEN_DIR / "golden.zip", GOLDEN_DIR / "golden.sample.zip")


@dataclass
class Package:
    """Un package modifiable : son nom de fichier, son dossier racine et ses fichiers."""

    name: str
    root: str | None
    files: dict[str, bytes]
    extra: dict[str, bytes] = field(default_factory=dict)

    def to_zip(self) -> bytes:
        return factories.build_zip(files=self.files, root=self.root, extra=self.extra)


def load_golden() -> Package:
    golden_file = next((path for path in GOLDEN_FILES if path.exists()), None)
    if golden_file is None:
        return Package(
            f"{factories.PACKAGE_NAME}.zip", factories.PACKAGE_NAME, factories.default_files()
        )
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(golden_file) as archive:
        roots = {n.split("/", 1)[0] for n in archive.namelist() if n.strip("/")}
        (root,) = roots
        for info in archive.infolist():
            if not info.is_dir():
                files[info.filename.split("/", 1)[1]] = archive.read(info)
    return Package(f"{root}.zip", root, files)
