# SPDX-License-Identifier: EUPL-1.2
"""Met en forme une archive de test comme celle d'un outil de production de registres.

Ajoute les entrées de dossiers manquantes (le chemin de chaque fichier est gardé tel quel) et
laisse les fichiers compressés en deflate. Ne touche jamais à une archive illisible : une faute
de structure voulue (archive corrompue, chiffrée, trop grande) doit rester telle quelle.
"""

import io
import zipfile

# Cas dont le fichier est un package valide : seule la mise en forme peut changer.
PACKAGE_PREFIXES = ("PKG-", "CSV-", "DAT-", "IMP-")


def with_directories(data: bytes) -> bytes:
    try:
        source = zipfile.ZipFile(io.BytesIO(data))
        if source.testzip() is not None:
            return data
        entries = source.infolist()
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
        return data
    out = io.BytesIO()
    written: set[str] = set()
    try:
        with zipfile.ZipFile(out, "w") as target:
            for info in entries:
                if info.is_dir():
                    continue
                parts = info.filename.split("/")
                for depth in range(1, len(parts)):
                    folder = "/".join(parts[:depth]) + "/"
                    if folder not in written:
                        target.writestr(folder, b"", compress_type=zipfile.ZIP_STORED)
                        written.add(folder)
                target.writestr(
                    info.filename, source.read(info), compress_type=zipfile.ZIP_DEFLATED
                )
    except (RuntimeError, NotImplementedError, zipfile.BadZipFile):
        return data
    return out.getvalue()
