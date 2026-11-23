# SPDX-License-Identifier: EUPL-1.2
"""Écrit tous les fichiers mutés du golden dans un dossier, pour les tester à la main.

Usage : python -m tests.cases.export_mutations DOSSIER
Chaque cas a son sous-dossier <cas>/ avec le fichier sous son nom d'origine (le nom compte pour
PKG-002) ; index.csv liste cas, code attendu et fichier.
Ces fichiers sont dérivés du golden : à ne pas versionner s'il contient des données réelles.
"""

import copy
import csv
import sys
from pathlib import Path

from tests.cases.golden import load_golden
from tests.cases.mutations import MUTATIONS
from tests.cases.zip_layout import PACKAGE_PREFIXES, with_directories


def main(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    golden = load_golden()
    with (target / "index.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cas", "code_attendu", "autres_codes_normaux", "description", "fichier"])
        for mutation in MUTATIONS:
            name, content = mutation.apply(copy.deepcopy(golden))
            folder = target / mutation.case
            folder.mkdir(exist_ok=True)
            if mutation.code.startswith(PACKAGE_PREFIXES) and name.endswith(".zip"):
                content = with_directories(content)
            (folder / name).write_bytes(content)
            also = " ".join(mutation.also)
            relative = f"{mutation.case}/{name}"
            writer.writerow([mutation.case, mutation.code, also, mutation.description, relative])
    print(f"{len(MUTATIONS)} fichiers écrits dans {target}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
