# SPDX-License-Identifier: EUPL-1.2
# ruff: noqa: E501
"""Cas de test par mutation : chaque cas introduit UNE erreur volontaire dans le package golden.

Un cas = (identifiant, code attendu, description, fonction de mutation). La fonction reçoit une
copie du package golden et retourne (nom du fichier déposé, contenu). ``also`` liste les autres
codes qui accompagnent normalement l'erreur (effets de bord connus).
"""

import csv
import io
import struct
from collections.abc import Callable
from dataclasses import dataclass, field

from contracts.naming import file_name_from_table_code
from tests import factories
from tests.cases.golden import Package

LEI_OTHER = "5493001KJTIIGC8Y1R12"
EUID = "eba_qCO:qx2002"
CRN = "eba_qCO:qx2003"
VAT = "eba_qCO:qx2004"
PASSPORT = "eba_qCO:qx2005"
LEI = "eba_qCO:qx2000"
NATURAL_PERSON_TYPE = "eba_CT:x213"
Delivery = tuple[str, bytes]


@dataclass(frozen=True)
class Mutation:
    case: str
    code: str
    description: str
    apply: Callable[[Package], Delivery]
    also: tuple[str, ...] = field(default=())


# ------------------------------------------------------------------ helpers
def _path(table: str) -> str:
    return f"reports/{file_name_from_table_code(table)}"


def _rows(pkg: Package, table: str) -> tuple[list[str], list[list[str]]]:
    reader = csv.reader(io.StringIO(pkg.files[_path(table)].decode("utf-8")))
    header = next(reader)
    return header, list(reader)


def _write(pkg: Package, table: str, header: list[str], rows: list[list[str]]) -> None:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    pkg.files[_path(table)] = out.getvalue().encode()


def add_row(pkg: Package, table: str, **cells: str) -> None:
    header, rows = _rows(pkg, table)
    rows.append([cells.get(column, "") for column in header])
    _write(pkg, table, header, rows)


def drop_column(pkg: Package, table: str, column: str) -> None:
    header, rows = _rows(pkg, table)
    index = header.index(column)
    _write(
        pkg, table, header[:index] + header[index + 1 :], [r[:index] + r[index + 1 :] for r in rows]
    )


def _add_empty_header_cell(content: bytes) -> bytes:
    """Trailing comma at the end of the header row, whatever the line ending."""
    end = content.index(b"\n")
    if end and content[end - 1 : end] == b"\r":
        end -= 1
    return content[:end] + b"," + content[end:]


def _widen_header(content: bytes, columns: int) -> bytes:
    """The header row stretched to ``columns`` distinct names; the data rows are left as they are."""
    header, rest = content.split(b"\n", 1)
    end = b"\r" if header.endswith(b"\r") else b""
    names = header.removesuffix(b"\r").split(b",")
    extra = [f"c{9000 + index}".encode() for index in range(columns - len(names))]
    return b",".join(names + extra) + end + b"\n" + rest


def empty_cell(pkg: Package, table: str, column: str, row: int = 0) -> None:
    """Empty one cell of an existing row (first data row by default)."""
    header, rows = _rows(pkg, table)
    rows[row][header.index(column)] = ""
    _write(pkg, table, header, rows)


def file_text(pkg: Package, path: str, old: str, new: str) -> None:
    pkg.files[path] = pkg.files[path].decode("utf-8").replace(old, new, 1).encode()


def _lines(pkg: Package, path: str) -> tuple[list[str], str]:
    text = pkg.files[path].decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.split(newline), newline


def drop_line(pkg: Package, path: str, prefix: str) -> None:
    """Remove the first line that starts with ``prefix`` (any line ending)."""
    lines, newline = _lines(pkg, path)
    index = next(i for i, line in enumerate(lines) if line.startswith(prefix))
    pkg.files[path] = newline.join(lines[:index] + lines[index + 1 :]).encode()


def set_parameter(pkg: Package, name: str, value: str) -> None:
    lines, newline = _lines(pkg, "reports/parameters.csv")
    lines = [f"{name},{value}" if line.startswith(f"{name},") else line for line in lines]
    pkg.files["reports/parameters.csv"] = newline.join(lines).encode()


def insert_after_header(pkg: Package, path: str, line: str) -> None:
    lines, newline = _lines(pkg, path)
    pkg.files[path] = newline.join([lines[0], line, *lines[1:]]).encode()


def entity_lei(pkg: Package) -> str:
    """LEI of the reporting entity, read from parameters.csv (rs:<LEI>.CON)."""
    lines, _ = _lines(pkg, "reports/parameters.csv")
    entity = next(line for line in lines if line.startswith("entityID,")).split(",", 1)[1]
    return entity.split(":", 1)[1].split(".", 1)[0]


def _zip(pkg: Package) -> Delivery:
    return pkg.name, pkg.to_zip()


def package_case(case: str, code: str, description: str, edit, *, also=(), name=None) -> Mutation:
    def apply(pkg: Package) -> Delivery:
        edit(pkg)
        return (name or pkg.name), pkg.to_zip()

    return Mutation(case, code, description, apply, tuple(also))


def envelope_case(case: str, code: str, description: str, *, also=(), **options) -> Mutation:
    def apply(pkg: Package) -> Delivery:
        settings = {"sender": entity_lei(pkg), **options}
        return "delivery.xml", factories.build_envelope(pkg.to_zip(), **settings)

    return Mutation(case, code, description, apply, tuple(also))


def raw_case(
    case: str, code: str, description: str, name: str, content: bytes, *, also=()
) -> Mutation:
    return Mutation(case, code, description, lambda pkg: (name, content), tuple(also))


def _set_lei_row(pkg: Package, value: str) -> None:
    add_row(pkg, "B_01.02", c0010=value)


def _set_euid_row(pkg: Package, value: str, country: str = "eba_GA:FR") -> None:
    add_row(pkg, "B_05.01", c0010=value, c0020=EUID, c0080=country)


def _set_branch_row(pkg: Package) -> None:
    """A branch whose code is the LEI of an entity already declared in B_01.02."""
    _, rows = _rows(pkg, "B_01.02")
    lei = rows[0][0] if rows and rows[0][0] else factories.LEI
    if not rows:
        add_row(pkg, "B_01.02", c0010=lei)
    add_row(pkg, "B_01.03", c0010=lei, c0020=lei)


def _set_branch_usage_row(pkg: Package, nature: str = "eba_ZZ:x838") -> None:
    """A contract used by a branch (B_04.01.0030 = branch) whose branch code is empty."""
    _, entities = _rows(pkg, "B_01.02")
    lei = entities[0][0] if entities and entities[0][0] else factories.LEI
    if not entities:
        add_row(pkg, "B_01.02", c0010=lei)
    _, contracts = _rows(pkg, "B_02.01")
    contract = contracts[0][0] if contracts and contracts[0][0] else "CONTRAT-SUCC"
    if not contracts:
        add_row(pkg, "B_02.01", c0010=contract)
    add_row(pkg, "B_04.01", c0010=contract, c0020=lei, c0030=nature)


# ------------------------------------------------------------------ Sprint 3 (lot 1, entités)
EF = "529900P784EKW7VFMQ21"  # entité qui tient le registre du golden
TOP = "529900R81VAA8RCKLQ52"  # mère ultime du groupe (x53)
SECOND_FE = "529900WFW9ZXG409UL36"
INTRA_GROUP = "5299003U9L1RY87FL751"
PARENT_A = "5299001KGZ7JIYCF3247"  # mère ultime de PSEUDO FOURNISSEUR A
PROVIDER_A = "529900KIWVWB8P3VEK25"


def set_where(pkg: Package, table: str, key: str, value: str, column: str, new: str) -> None:
    """Change one cell of the row whose ``key`` column equals ``value``."""
    header, rows = _rows(pkg, table)
    row = next(r for r in rows if r[header.index(key)] == value)
    row[header.index(column)] = new
    _write(pkg, table, header, rows)


NATURAL_PERSON = "X4RTBPFW4"


def add_provider(pkg: Package, code: str, kind: str, name: str, country: str = "eba_GA:FR") -> None:
    """A complete provider row of B_05.01, its own ultimate parent."""
    add_row(
        pkg,
        "B_05.01",
        c0010=code,
        c0020=kind,
        c0050=name,
        c0060=name,
        c0070="eba_CT:x212",
        c0080=country,
        c0090="eba_CU:EUR",
        c0100="0",
        c0110=code,
        c0120=kind,
    )


def _add_function(pkg: Package, code: str, entity: str, critical: str, name: str = "") -> None:
    """A complete row of B_06.01 that no row of B_02.02 cites."""
    add_row(
        pkg,
        "B_06.01",
        c0010=code,
        c0020="eba_TA:x182",
        c0030=name or f"FONCTION AJOUTEE {code}",
        c0040=entity,
        c0050=critical,
        c0060="FONCTION DE TEST",
        c0070="2026-10-19",
        c0080="48",
        c0090="48",
        c0100="eba_ZZ:x791",
    )


def _critical_without_lei(pkg: Package) -> None:
    """The provider of CONTRAT DIRECT EF (critical F1) changes to a national code everywhere."""
    old, new = "529900KIWVWB8P3VEK25", "X1YZ234AB"
    for table, column, type_column in (
        ("B_05.01", "c0010", "c0020"),
        ("B_02.02", "c0030", "c0040"),
        ("B_05.02", "c0030", "c0040"),
        ("B_05.02", "c0060", "c0070"),
        ("B_03.02", "c0020", "c0030"),
        ("B_07.01", "c0020", "c0030"),
    ):
        header, rows = _rows(pkg, table)
        for row in rows:
            if row[header.index(column)] == old:
                row[header.index(column)] = new
                row[header.index(type_column)] = "eba_qCO:qx2001"
        _write(pkg, table, header, rows)


def delete_where(pkg: Package, table: str, **match: str) -> None:
    """Remove the rows whose columns equal every value given."""
    header, rows = _rows(pkg, table)
    kept = [r for r in rows if any(r[header.index(c)] != v for c, v in match.items())]
    assert len(kept) < len(rows), (table, match)
    _write(pkg, table, header, kept)


def _add_framework_of_wrong_type(pkg: Package) -> None:
    """A subsequent contract (x3) citing a contract that exists but is not a framework (x2)."""
    add_row(pkg, "B_02.01", c0010="CONTRAT-NONCADRE", c0020="eba_CO:x1")
    add_row(
        pkg,
        "B_02.01",
        c0010="CONTRAT-SUBSEQ",
        c0020="eba_CO:x3",
        c0030="CONTRAT-NONCADRE",
    )


def _add_unsigned_provider(pkg: Package) -> None:
    """Copy a row of B_02.02 with a provider that does not sign the contract in B_03.02."""
    header, rows = _rows(pkg, "B_02.02")
    if not rows:
        add_row(pkg, "B_02.02", c0010="CONTRAT-R17", c0030=LEI_OTHER)
        return
    row = list(rows[0])
    row[header.index("c0030")] = LEI_OTHER
    rows.append(row)
    _write(pkg, "B_02.02", header, rows)


def _corrupt(data: bytes) -> bytes:
    middle = len(data) // 2
    return data[:middle] + bytes([data[middle] ^ 0xFF]) + data[middle + 1 :]


ZIP_CENTRAL_ENTRY = b"PK\x01\x02"
ZIP_LOCAL_ENTRY = b"PK\x03\x04"


def _patch_zip_entries(data: bytes, signature: bytes, offset: int, patch) -> bytes:
    """Rewrite one field in every header of an archive that starts with ``signature``."""
    out = bytearray(data)
    start = out.find(signature)
    while start >= 0:
        patch(out, start + offset)
        start = out.find(signature, start + len(signature))
    return bytes(out)


def _with_duplicate(data: bytes, name: str) -> bytes:
    """The archive with a second member of the same name (zipfile only warns)."""
    import warnings
    import zipfile

    buffer = io.BytesIO(data)
    with warnings.catch_warnings(), zipfile.ZipFile(buffer, "a") as archive:
        warnings.simplefilter("ignore")
        archive.writestr(name, b"c0010\nautre contenu\n")
    return buffer.getvalue()


def _password_protected(data: bytes) -> bytes:
    """Set the "encrypted" flag (bit 0) on every entry, as a password-protected ZIP does."""

    def flag(out: bytearray, at: int) -> None:
        out[at] |= 0x01

    data = _patch_zip_entries(data, ZIP_CENTRAL_ENTRY, 8, flag)
    return _patch_zip_entries(data, ZIP_LOCAL_ENTRY, 6, flag)


def _declared_size(data: bytes, megabytes: int) -> bytes:
    """Declare a huge uncompressed size on every entry (the signature of a zip bomb)."""

    def size(out: bytearray, at: int) -> None:
        out[at : at + 4] = struct.pack("<I", megabytes * 1024 * 1024)

    return _patch_zip_entries(data, ZIP_CENTRAL_ENTRY, 24, size)


def _latin1_envelope(pkg: Package) -> bytes:
    """An envelope that declares UTF-8 but carries a Latin-1 accent."""
    return factories.build_envelope(pkg.to_zip()).replace(
        b"<Email>reporting@", b"<Email>reporting\xe9@", 1
    )


def _del(path: str):
    return lambda pkg: pkg.files.pop(path)


# ------------------------------------------------------------------ catalogue
MUTATIONS: tuple[Mutation, ...] = (
    # Fichier déposé
    raw_case("M-FILE-001", "FILE-001", "contenu ni XML ni ZIP", "notes.bin", b"hello world"),
    raw_case("M-FILE-002", "FILE-002", "fichier vide", "empty.zip", b""),
    raw_case(
        "M-ZIP-001",
        "ZIP-001",
        "archive tronquée après l'en-tête",
        "broken.zip",
        b"PK\x03\x04" + b"\x00" * 40,
        also=("ZIP-002",),
    ),
    package_case(
        "M-ZIP-006",
        "ZIP-006",
        "chemin dangereux ../",
        lambda p: p.extra.update({"../evil.txt": b"x"}),
        also=("PKG-001",),
    ),
    Mutation(
        "M-ZIP-009",
        "ZIP-009",
        "deux fichiers du même nom dans l'archive",
        lambda p: (p.name, _with_duplicate(p.to_zip(), f"{p.root}/reports/b_01.01.csv")),
    ),
    package_case(
        "M-ZIP-007",
        "ZIP-007",
        "archive imbriquée",
        lambda p: p.files.update({"reports/inner.zip": b"PK\x03\x04"}),
        also=("PKG-007",),
    ),
    # Enveloppe XML
    raw_case(
        "M-XML-002", "XML-002", "XML mal formé", "bad.xml", b"<XbrlDelivery><oops></XbrlDelivery>"
    ),
    raw_case(
        "M-XML-003",
        "XML-003",
        "déclaration DOCTYPE",
        "doctype.xml",
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><XbrlDelivery/>',
    ),
    raw_case("M-ENV-001", "ENV-001", "élément racine inconnu", "other.xml", b"<Other/>"),
    envelope_case("M-ENV-002", "ENV-002", "deux déclarations", declarations=2),
    envelope_case("M-ENV-003", "ENV-003", "élément <csv> vide", payload=" "),
    envelope_case("M-ENV-004", "ENV-004", "base 64 invalide", payload="!!!pas-du-base64!!!"),
    envelope_case("M-ENV-005", "ENV-005", "destinataire différent de BDF", recipient="XXX"),
    envelope_case("M-ENV-006", "ENV-006", "domaine inconnu", domain="ABC"),
    envelope_case("M-ENV-007", "ENV-007", "attribut action absent", action=None),
    envelope_case("M-ENV-008", "ENV-008", "expéditeur invalide", sender="BAD"),
    envelope_case(
        "M-ENV-009", "ENV-009", "LEI de l'enveloppe différent du package", sender=LEI_OTHER
    ),
    envelope_case("M-ENV-010", "ENV-010", "aucune déclaration", declarations=0),
    # Package
    package_case(
        "M-PKG-001", "PKG-001", "pas de dossier racine", lambda p: setattr(p, "root", None)
    ),
    package_case(
        "M-PKG-002",
        "PKG-002",
        "nom du ZIP différent du dossier racine",
        lambda p: None,
        name="autre.zip",
    ),
    package_case(
        "M-PKG-003",
        "PKG-003",
        "nom de package non conforme",
        lambda p: setattr(p, "root", "mon-registre"),
        also=("PKG-002",),
    ),
    package_case(
        "M-PKG-004",
        "PKG-004",
        "dossier inattendu",
        lambda p: p.files.update({"docs/notes.txt": b"x"}),
        also=("PKG-007",),
    ),
    package_case(
        "M-PKG-005", "PKG-005", "fichier obligatoire manquant", _del("reports/parameters.csv")
    ),
    package_case(
        "M-PKG-006",
        "PKG-006",
        "report.json invalide",
        lambda p: p.files.update({"reports/report.json": b"{"}),
    ),
    package_case(
        "M-PKG-007",
        "PKG-007",
        "fichier non décrit",
        lambda p: p.files.update({"reports/register.xlsx": b"x"}),
    ),
    package_case(
        "M-PKG-008",
        "PKG-008",
        "deux fichiers à la casse près",
        lambda p: p.files.update({"reports/B_01.01.csv": p.files["reports/b_01.01.csv"]}),
        also=("PKG-018",),
    ),
    package_case(
        "M-PKG-009",
        "PKG-009",
        "taxonomie non prise en charge",
        lambda p: file_text(p, "reports/report.json", "/4.0/", "/9.9/"),
        also=("PKG-019",),
    ),
    package_case(
        "M-PKG-010", "PKG-010", "tableau déclaré mais fichier absent", _del("reports/b_02.01.csv")
    ),
    package_case(
        "M-PKG-011",
        "PKG-011",
        "tableau absent de FilingIndicators",
        lambda p: drop_line(p, "reports/FilingIndicators.csv", "B_02.01,"),
    ),
    package_case(
        "M-PKG-012",
        "PKG-012",
        "indicateur false avec fichier présent",
        lambda p: file_text(p, "reports/FilingIndicators.csv", "B_02.01,true", "B_02.01,false"),
    ),
    package_case(
        "M-PKG-013",
        "PKG-013",
        "indicateur de remise invalide",
        lambda p: file_text(p, "reports/FilingIndicators.csv", "B_02.01,true", "B_02.01,oui"),
    ),
    package_case(
        "M-PKG-014",
        "PKG-014",
        "paramètre manquant",
        lambda p: drop_line(p, "reports/parameters.csv", "baseCurrency,"),
    ),
    package_case(
        "M-PKG-015",
        "PKG-015",
        "paramètre inattendu",
        lambda p: file_text(p, "reports/parameters.csv", "refPeriod", "extra,1\nrefPeriod"),
    ),
    package_case(
        "M-PKG-016",
        "PKG-016",
        "LEI du nom différent de l'entityID",
        lambda p: set_parameter(p, "entityID", f"rs:{LEI_OTHER}.CON"),
        also=("PKG-021",),
    ),
    package_case(
        "M-PKG-017",
        "PKG-017",
        "date de référence différente",
        lambda p: set_parameter(p, "refPeriod", "2019-12-31"),
    ),
    package_case(
        "M-PKG-018",
        "PKG-018",
        "nom de fichier en majuscules",
        lambda p: p.files.update({"reports/B_01.01.csv": p.files.pop("reports/b_01.01.csv")}),
        also=("PKG-005", "PKG-010"),
    ),
    package_case(
        "M-PKG-020",
        "PKG-020",
        "modèle inconnu déclaré",
        lambda p: insert_after_header(p, "reports/FilingIndicators.csv", "B_99.99,true"),
    ),
    package_case(
        "M-PKG-022",
        "PKG-022",
        "indicateur écrit 1 au lieu de true",
        lambda p: file_text(p, "reports/FilingIndicators.csv", "B_02.01,true", "B_02.01,1"),
    ),
    # CSV
    package_case(
        "M-CSV-001",
        "CSV-001",
        "fichier non UTF-8",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": p.files["reports/b_01.01.csv"] + b"\xe9\xff\n"}
        ),
    ),
    package_case(
        "M-CSV-002",
        "CSV-002",
        "marque BOM",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": b"\xef\xbb\xbf" + p.files["reports/b_01.01.csv"]}
        ),
    ),
    package_case(
        "M-CSV-003",
        "CSV-003",
        "fichier sans en-tête",
        lambda p: p.files.update({"reports/b_01.01.csv": b""}),
    ),
    package_case(
        "M-CSV-004",
        "CSV-004",
        "ligne trop longue",
        lambda p: p.files.update(
            {
                "reports/b_01.01.csv": p.files["reports/b_01.01.csv"]
                + b"a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p\n"
            }
        ),
    ),
    package_case(
        "M-CSV-005",
        "CSV-005",
        "séparateur point-virgule",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": p.files["reports/b_01.01.csv"].replace(b",", b";")}
        ),
    ),
    package_case(
        "M-CSV-006",
        "CSV-006",
        "cellule d'en-tête vide (virgule en trop en fin d'en-tête)",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": _add_empty_header_cell(p.files["reports/b_01.01.csv"])}
        ),
    ),
    package_case(
        "M-CSV-007",
        "CSV-007",
        "en-tête en double",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": p.files["reports/b_01.01.csv"].replace(b"c0020", b"c0010", 1)}
        ),
        also=("CSV-004",),
    ),
    # Plafonds de l'import (CL-46, décisions du PO du 07/11/2026)
    package_case(
        "M-CSV-008",
        "CSV-008",
        "cellule de 10 001 caractères (limite : 10 000)",
        lambda p: set_where(p, "B_05.01", "c0010", "529900KIWVWB8P3VEK25", "c0050", "N" * 10_001),
    ),
    package_case(
        "M-CSV-009",
        "CSV-009",
        "ligne d'en-têtes de 201 colonnes (limite : 200)",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": _widen_header(p.files["reports/b_01.01.csv"], 201)}
        ),
    ),
    package_case(
        "M-CSV-010",
        "CSV-010",
        "registre de plus de 2 000 000 lignes, tous tableaux confondus",
        lambda p: p.files.update(
            {"reports/b_99.01.csv": p.files["reports/b_99.01.csv"] + b"x\n" * 2_000_000}
        ),
        also=("IMP-001",),
    ),
    # Fins de ligne (contrôle BCE du 02/10/2026, décision du PO du 09/11/2026)
    package_case(
        "M-CSV-011",
        "CSV-011",
        "dernière ligne sans saut de ligne",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": p.files["reports/b_01.01.csv"].rstrip(b"\r\n")}
        ),
    ),
    package_case(
        "M-CSV-012",
        "CSV-012",
        "fin de ligne en retour chariot seul (CR)",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": p.files["reports/b_01.01.csv"].rstrip(b"\r\n") + b"\r"}
        ),
    ),
    # Données
    package_case(
        "M-DAT-001",
        "DAT-001",
        "colonne inconnue",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": p.files["reports/b_01.01.csv"].replace(b"c0020", b"c9999", 1)}
        ),
        also=(
            "DAT-003",
            "DAT-030",
        ),
    ),
    package_case(
        "M-DAT-002",
        "DAT-002",
        "B_01.01 sans donnée",
        lambda p: p.files.update(
            {"reports/b_01.01.csv": p.files["reports/b_01.01.csv"].split(b"\n")[0] + b"\n"}
        ),
    ),
    package_case(
        "M-DAT-003",
        "DAT-003",
        "clé primaire vide",
        lambda p: add_row(p, "B_01.02", c0020="Sans clé"),
    ),
    package_case(
        "M-DAT-004",
        "DAT-004",
        "clé primaire en double",
        lambda p: [_set_lei_row(p, factories.LEI), _set_lei_row(p, factories.LEI)],
    ),
    package_case(
        "M-DAT-005",
        "DAT-005",
        "clé étrangère sans correspondance",
        lambda p: add_row(p, "B_03.01", c0010="X1", c0020=LEI_OTHER),
    ),
    package_case(
        "M-DAT-006", "DAT-006", "LEI de 19 caractères", lambda p: _set_lei_row(p, LEI_OTHER[:-1])
    ),
    package_case(
        "M-DAT-007", "DAT-007", "LEI en minuscules", lambda p: _set_lei_row(p, LEI_OTHER.lower())
    ),
    package_case(
        "M-DAT-008",
        "DAT-008",
        "LEI sans deux chiffres finaux",
        lambda p: _set_lei_row(p, LEI_OTHER[:-2] + "AB"),
    ),
    package_case(
        "M-DAT-009",
        "DAT-009",
        "LEI avec espace au début",
        lambda p: _set_lei_row(p, " " + LEI_OTHER),
    ),
    package_case(
        "M-DAT-010",
        "DAT-010",
        "LEI à la clé de contrôle fausse",
        lambda p: _set_lei_row(p, LEI_OTHER[:-2] + "13"),
    ),
    package_case(
        "M-DAT-011", "DAT-011", "EUID sans préfixe pays", lambda p: _set_euid_row(p, "116737")
    ),
    package_case(
        "M-DAT-012",
        "DAT-012",
        "EUID d'un pays hors EEE",
        lambda p: _set_euid_row(p, "US12345", "eba_GA:US"),
        also=("DAT-031",),
    ),
    package_case(
        "M-DAT-013",
        "DAT-013",
        "EUID FR avec siège en Allemagne",
        lambda p: _set_euid_row(p, "FRRCSPARIS.394199723", "eba_GA:DE"),
    ),
    package_case(
        "M-DAT-031",
        "DAT-031",
        "EUID sans point entre registre et numéro (information)",
        lambda p: _set_euid_row(p, "DEK1101RHRB116737", "eba_GA:DE"),
    ),
    package_case(
        "M-DAT-032",
        "DAT-032",
        "possibilité de réintégration (RT.07.01.0090) laissée vide",
        lambda p: empty_cell(p, "B_07.01", "c0090"),
    ),
    package_case(
        "M-DAT-015",
        "DAT-015",
        "montant avec suffixe de décimales (78920030d-4)",
        lambda p: add_row(
            p, "B_05.01", c0010="FRRCSPARIS.394199723", c0020=EUID, c0100="78920030d-4"
        ),
    ),
    package_case(
        "M-PKG-023",
        "PKG-023",
        "decimalsMonetary à -5 (précision insuffisante)",
        lambda p: file_text(
            p, "reports/parameters.csv", "decimalsMonetary,-3", "decimalsMonetary,-5"
        ),
    ),
    package_case(
        "M-PKG-024",
        "PKG-024",
        "ZIP recompressé sur Mac : dossier __MACOSX et fichiers ._* ajoutés",
        lambda p: p.extra.update(
            {"__MACOSX/._package": b"x", "__MACOSX/" + p.root + "/._report.json": b"x"}
        ),
    ),
    package_case(
        "M-PKG-026",
        "PKG-026",
        "reports/FootNotes.csv ajouté (accepté et ignoré)",
        lambda p: p.files.update({"reports/FootNotes.csv": b"x\n"}),
    ),
    package_case(
        "M-PKG-025",
        "PKG-025",
        "chemin écrit avec \\ au lieu de / dans l'archive",
        lambda p: p.files.update(
            {"reports\\parameters.csv": p.files.pop("reports/parameters.csv")}
        ),
    ),
    package_case(
        "M-DAT-014",
        "DAT-014",
        "TVA française déclarée comme EUID",
        lambda p: _set_euid_row(p, "FR12394199723"),
    ),
    package_case(
        "M-DAT-016",
        "DAT-016",
        "EUID français sans SIREN final",
        lambda p: _set_euid_row(p, "FRRCS.ABC"),
    ),
    package_case(
        "M-DAT-017",
        "DAT-017",
        "numéro d'immatriculation français de 8 chiffres",
        lambda p: add_row(p, "B_05.01", c0010="39419972", c0020=CRN, c0080="eba_GA:FR"),
    ),
    package_case(
        "M-DAT-018",
        "DAT-018",
        "TVA française sans clé",
        lambda p: add_row(p, "B_05.01", c0010="FR394199723", c0020=VAT, c0080="eba_GA:FR"),
    ),
    package_case(
        "M-DAT-019",
        "DAT-019",
        "code supplémentaire déclaré comme passeport",
        lambda p: add_row(p, "B_05.01", c0010="394199723", c0020=CRN, c0030="X1", c0040=PASSPORT),
    ),
    package_case(
        "M-DAT-020",
        "DAT-020",
        "code supplémentaire identique au code principal",
        lambda p: add_row(p, "B_05.01", c0010="394199723", c0020=CRN, c0030="394199723", c0040=CRN),
    ),
    package_case(
        "M-DAT-021",
        "DAT-021",
        "succursale identifiée par le LEI du siège",
        lambda p: _set_branch_row(p),
    ),
    package_case(
        "M-DAT-022",
        "DAT-022",
        "nom de prestataire de 256 caractères",
        lambda p: add_row(p, "B_05.01", c0010="394199723", c0020=CRN, c0050="é" * 256),
    ),
    package_case(
        "M-DAT-023",
        "DAT-023",
        "type d'arrangement contractuel sans devise ni montant (règle EBA de groupe)",
        lambda p: add_row(p, "B_02.01", c0010="CONTRACTMUT01", c0020="eba_CO:x1"),
        also=("REL-009", "REL-010", "REL-011", "DQ-005"),
    ),
    package_case(
        "M-DAT-024",
        "DAT-024",
        "arrangement subséquent sans référence de l'arrangement cadre (valeur codifiée)",
        lambda p: add_row(p, "B_02.01", c0010="CONTRACTMUT02", c0020="eba_CO:x3"),
        also=("REL-009", "REL-010", "REL-011", "DQ-005"),
    ),
    package_case(
        "M-DAT-025",
        "DAT-025",
        "total de bilan non numérique",
        lambda p: add_row(p, "B_01.02", c0010=LEI_OTHER, c0110="abc"),
    ),
    package_case(
        "M-DAT-026",
        "DAT-026",
        "total de bilan négatif",
        lambda p: add_row(p, "B_01.02", c0010=LEI_OTHER, c0110="-5"),
    ),
    package_case(
        "M-DAT-027",
        "DAT-027",
        "succursale déclarée en RT.04.01 sans code de succursale",
        lambda p: _set_branch_usage_row(p),
    ),
    package_case(
        "M-DAT-028",
        "DAT-028",
        "non-succursale avec code de succursale vide au lieu de Not Applicable",
        lambda p: _set_branch_usage_row(p, nature="eba_ZZ:x839"),
    ),
    package_case(
        "M-DAT-029",
        "DAT-029",
        "accord-cadre cité en RT.02.01.0030 qui n'est pas de type eba_CO:x2",
        lambda p: _add_framework_of_wrong_type(p),
        also=("REL-009", "REL-010", "REL-011", "DQ-005"),
    ),
    package_case(
        "M-DAT-030",
        "DAT-030",
        "colonne facultative RT.07.01.0120 absente de l'en-tête",
        lambda p: drop_column(p, "B_07.01", "c0120"),
    ),
    package_case(
        "M-DAT-005-R17",
        "DAT-005",
        "sous-traitant déclaré en RT.02.02 sans être signataire en RT.03.02 (contrainte R17)",
        lambda p: _add_unsigned_provider(p),
        also=("DAT-003", "REL-013"),  # DAT-003 : package synthétique seulement
    ),
    # Cas fabriqués à la main
    Mutation(
        "M-ENV-011",
        "ENV-011",
        "espace de noms OneGate erroné",
        lambda p: (
            "ns.xml",
            factories.build_envelope(p.to_zip()).replace(
                b"http://www.onegate.eu/2010-01-01", b"http://example.org/ns"
            ),
        ),
    ),
    Mutation(
        "M-ZIP-008",
        "ZIP-008",
        "archive sans aucune entrée",
        lambda p: ("empty-archive.zip", b"PK\x05\x06" + b"\x00" * 18),
    ),
    Mutation(
        "M-ZIP-002",
        "ZIP-002",
        "octet altéré dans une entrée (CRC)",
        lambda p: ("crc.zip", _corrupt(p.to_zip())),
    ),
    Mutation(
        "M-XML-001",
        "XML-001",
        "encodage déclaré (UTF-8) incompatible avec le contenu (accent Latin-1)",
        lambda p: ("latin1.xml", _latin1_envelope(p)),
    ),
    Mutation(
        "M-ZIP-003",
        "ZIP-003",
        "archive protégée par mot de passe (indicateur de chiffrement)",
        lambda p: (p.name, _password_protected(p.to_zip())),
    ),
    package_case(
        "M-ZIP-004",
        "ZIP-004",
        "plus d'entrées que la limite (200 par défaut)",
        lambda p: p.extra.update({f"surplus/{i}.txt": b"x" for i in range(201)}),
    ),
    Mutation(
        "M-ZIP-005",
        "ZIP-005",
        "taille décompressée déclarée (600 Mo) au-dessus de la limite (500 Mo)",
        lambda p: (p.name, _declared_size(p.to_zip(), 600)),
    ),
    package_case(
        "M-IMP-001",
        "IMP-001",
        "dossier racine valide mais aucun fichier de table",
        lambda p: setattr(p, "files", {"reports/notes.txt": b"x"}),
        also=("PKG-005", "PKG-007", "PKG-010"),
    ),
    package_case(
        "M-PKG-019",
        "PKG-019",
        "code de module incompatible avec la taxonomie",
        lambda p: setattr(p, "root", p.root.replace("DORA010100", "DORA020100")),
        name="x.zip",
        also=("PKG-002",),
    ),
    package_case(
        "M-PKG-021",
        "PKG-021",
        "périmètre du nom différent de l'entityID",
        lambda p: file_text(p, "reports/parameters.csv", ".CON", ".IND"),
        also=(),
    ),
    package_case(
        "M-REL-001",
        "REL-001",
        "entité qui tient le registre absente de B_01.02 (LEI de B_01.01 remplacé)",
        lambda p: set_where(p, "B_01.01", "c0010", EF, "c0010", LEI_OTHER),
        also=("PKG-016",),
    ),
    package_case(
        "M-REL-002",
        "REL-002",
        "nom de l'entité différent entre B_01.01, B_01.02 et B_05.01",
        lambda p: set_where(p, "B_01.02", "c0010", EF, "c0020", "AUTRE ETABLISSEMENT"),
    ),
    package_case(
        "M-REL-003",
        "REL-003",
        "nom de l'entité écrit autrement (casse) dans B_01.02",
        lambda p: set_where(p, "B_01.02", "c0010", EF, "c0020", "Etablissement Financier Fictif"),
    ),
    package_case(
        "M-REL-004",
        "REL-004",
        "pays de l'entité différent entre B_01.02 et B_01.01, B_05.01",
        lambda p: set_where(p, "B_01.02", "c0010", EF, "c0030", "eba_GA:BE"),
    ),
    package_case(
        "M-REL-005",
        "REL-005",
        "mère ultime du prestataire intragroupe hors de la chaîne de ses mères",
        lambda p: set_where(p, "B_05.01", "c0010", INTRA_GROUP, "c0110", PARENT_A),
    ),
    package_case(
        "M-BUS-001",
        "BUS-001",
        "deux entités en position de mère ultime (x53)",
        lambda p: set_where(p, "B_01.02", "c0010", SECOND_FE, "c0050", "eba_RP:x53"),
    ),
    package_case(
        "M-BUS-002",
        "BUS-002",
        "chaîne des mères directes en boucle (mère ultime rattachée à sa fille)",
        lambda p: set_where(p, "B_01.02", "c0010", TOP, "c0060", EF),
    ),
    package_case(
        "M-BUS-003",
        "BUS-003",
        "type de code de la mère ultime différent du type déclaré pour cette mère",
        lambda p: set_where(p, "B_05.01", "c0010", PROVIDER_A, "c0120", CRN),
        also=("DAT-014",),
    ),
    package_case(
        "M-BUS-004",
        "BUS-004",
        "mère ultime d'un prestataire qui désigne une autre mère ultime",
        lambda p: set_where(p, "B_05.01", "c0010", PARENT_A, "c0110", PROVIDER_A),
    ),
    package_case(
        "M-BUS-005",
        "BUS-005",
        "date d'intégration postérieure à la dernière mise à jour (B_01.02)",
        lambda p: set_where(p, "B_01.02", "c0010", EF, "c0080", "2026-12-01"),
    ),
    package_case(
        "M-REL-006",
        "REL-006",
        "type de code du prestataire en B_03.02 différent de B_05.01.0020",
        lambda p: set_where(p, "B_03.02", "c0010", "CONTRAT DIRECT EF", "c0030", CRN),
        also=("DAT-014",),
    ),
    package_case(
        "M-REL-007",
        "REL-007",
        "prestataire direct déclaré personne morale, identifié par un code national",
        lambda p: set_where(p, "B_05.01", "c0010", NATURAL_PERSON, "c0070", "eba_CT:x212"),
        also=("BUS-019",),  # the consultant supports critical functions
    ),
    package_case(
        "M-DQ-001",
        "DQ-001",
        "même prestataire déclaré deux fois (même nom, forme juridique en plus, même pays)",
        lambda p: add_provider(p, LEI_OTHER, "eba_qCO:qx2000", "Pseudo Fournisseur A S.A.S."),
        also=("DQ-004",),
    ),
    package_case(
        "M-DQ-002",
        "DQ-002",
        "identifiant secondaire d'un prestataire égal à l'identifiant d'un autre prestataire",
        lambda p: (
            set_where(p, "B_05.01", "c0010", "197697980", "c0030", PROVIDER_A),
            set_where(p, "B_05.01", "c0010", "197697980", "c0040", "eba_qCO:qx2000"),
        ),
    ),
    package_case(
        "M-DQ-003",
        "DQ-003",
        "EUID français contenant le SIREN d'un prestataire déjà déclaré",
        lambda p: add_provider(p, "FRRCSPARIS.197697980", EUID, "FOURNISSEUR EUID"),
        also=("DQ-004",),
    ),
    package_case(
        "M-DQ-004",
        "DQ-004",
        "prestataire déclaré dans B_05.01 sans aucun accord ni chaîne",
        lambda p: add_provider(p, LEI_OTHER, "eba_qCO:qx2000", "FOURNISSEUR ISOLE"),
    ),
    package_case(
        "M-DQ-014",
        "DQ-014",
        "coût total du prestataire inférieur à la somme de ses accords (PO-35)",
        lambda p: set_where(p, "B_05.01", "c0010", "529900KIWVWB8P3VEK25", "c0100", "1000"),
    ),
    package_case(
        "M-DQ-015",
        "DQ-015",
        "devise du prestataire différente de celle de ses accords (PO-35)",
        lambda p: set_where(p, "B_05.01", "c0010", "197697980", "c0090", "eba_CU:USD"),
    ),
    package_case(
        "M-REL-008",
        "REL-008",
        "entité utilisatrice d'une ligne B_02.02 absente de B_04.01 pour ce contrat",
        lambda p: delete_where(p, "B_04.01", c0010="CONTRAT CONSULTANT", c0020=EF),
    ),
    package_case(
        "M-REL-009",
        "REL-009",
        "accord sans entité signataire dans B_03.01",
        lambda p: delete_where(p, "B_03.01", c0010="CONTRAT PARTAGE"),
    ),
    package_case(
        "M-REL-010",
        "REL-010",
        "accord sans aucune ligne dans B_02.02",
        lambda p: delete_where(p, "B_02.02", c0010="CONTRAT PARTAGE"),
        also=("REL-014",),
    ),
    package_case(
        "M-REL-011",
        "REL-011",
        "accord sans entité utilisatrice dans B_04.01",
        lambda p: delete_where(p, "B_04.01", c0010="CONTRAT PARTAGE"),
        also=("REL-008",),
    ),
    package_case(
        "M-DQ-005",
        "DQ-005",
        "accord de B_02.01 cité dans aucun autre tableau",
        lambda p: add_row(
            p, "B_02.01", c0010="CONTRAT ORPHELIN", c0020="eba_CO:x1", c0040="eba_CU:EUR", c0050="0"
        ),
        also=("REL-009", "REL-010", "REL-011"),
    ),
    package_case(
        "M-DQ-006",
        "DQ-006",
        "accord terminé avant la date de référence (motif de fin renseigné)",
        lambda p: (
            set_where(p, "B_02.02", "c0010", "CONTRAT DIRECT EF", "c0080", "2025-06-30"),
            set_where(p, "B_02.02", "c0010", "CONTRAT DIRECT EF", "c0090", "eba_CO:x4"),
        ),
    ),
    package_case(
        "M-DQ-007",
        "DQ-007",
        "accord-cadre cité par aucun accord subséquent",
        lambda p: set_where(p, "B_02.01", "c0010", "CONTRAT SUBSEQUENT PAR IG 1", "c0030", ""),
    ),
    package_case(
        "M-DQ-008",
        "DQ-008",
        "accord qui commence après la date de référence",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT IG LEVEL 0", "c0070", "2027-01-01"),
        also=("DQ-009",),
    ),
    package_case(
        "M-BUS-006",
        "BUS-006",
        "accord autonome (x1) qui cite un accord-cadre en B_02.01.0030",
        lambda p: set_where(
            p, "B_02.01", "c0010", "CONTRAT DIRECT EF", "c0030", "CONTRAT CADRE PAR IG"
        ),
    ),
    package_case(
        "M-BUS-007",
        "BUS-007",
        "accord subséquent signé avec un autre prestataire que son accord-cadre",
        lambda p: (
            set_where(p, "B_03.02", "c0010", "CONTRAT SUBSEQUENT PAR IG 1", "c0020", PROVIDER_A),
            set_where(
                p, "B_03.02", "c0010", "CONTRAT SUBSEQUENT PAR IG 1", "c0030", "eba_qCO:qx2000"
            ),
        ),
        also=("DAT-005", "DQ-014"),
    ),
    package_case(
        "M-BUS-008",
        "BUS-008",
        "date de début de l'accord postérieure à sa date de fin",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT DIRECT EF", "c0070", "2028-01-01"),
        also=("DQ-008",),
    ),
    package_case(
        "M-BUS-009",
        "BUS-009",
        "accord terminé sans motif de fin",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT EXPIRE", "c0090", ""),
    ),
    package_case(
        "M-BUS-010",
        "BUS-010",
        "motif de fin renseigné pour un accord en cours",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT DIRECT EF", "c0090", "eba_CO:x4"),
    ),
    package_case(
        "M-DQ-009",
        "DQ-009",
        "préavis de l'entité plus long que la durée de l'accord",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT DIRECT EF", "c0100", "5000"),
    ),
    package_case(
        "M-DQ-010",
        "DQ-010",
        "date de fin improbable (2150) au lieu de 9999-12-31",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT DIRECT EF", "c0080", "2150-12-31"),
    ),
    package_case(
        "M-BUS-011",
        "BUS-011",
        "droit applicable différent sur une ligne d'un même accord",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT INTRA GROUPE", "c0120", "eba_GA:DE"),
    ),
    # ------------------------------------------------------------ Sprint 3, lot 4 (fonctions)
    package_case(
        "M-BUS-012",
        "BUS-012",
        "identifiant de fonction qui ne suit pas la forme F + numéro",
        lambda p: (
            set_where(p, "B_06.01", "c0010", "F3", "c0010", "FCT3"),
            set_where(p, "B_02.02", "c0010", "CONTRAT IG LEVEL 0", "c0050", "FCT3"),
        ),
    ),
    package_case(
        "M-BUS-013",
        "BUS-013",
        "même identifiant de fonction pour deux entités",
        lambda p: _add_function(p, "F1", SECOND_FE, "eba_BT:x29", name="FONCTION BIS"),
        also=("DQ-011",),
    ),
    package_case(
        "M-REL-012",
        "REL-012",
        "fonction critique soutenue par aucun accord",
        lambda p: _add_function(p, "F5", EF, "eba_BT:x28"),
    ),
    package_case(
        "M-DQ-011",
        "DQ-011",
        "fonction non critique soutenue par aucun accord",
        lambda p: _add_function(p, "F5", EF, "eba_BT:x29"),
    ),
    package_case(
        "M-BUS-015",
        "BUS-015",
        "fonction critique avec un RTO à 0",
        lambda p: set_where(p, "B_06.01", "c0010", "F1", "c0080", "0"),
    ),
    package_case(
        "M-BUS-016",
        "BUS-016",
        "fonction critique sans justification de criticité",
        lambda p: set_where(p, "B_06.01", "c0010", "F1", "c0060", ""),
    ),
    package_case(
        "M-BUS-017",
        "BUS-017",
        "évaluation de criticité datée après la date de référence",
        lambda p: set_where(p, "B_06.01", "c0010", "F3", "c0070", "2027-03-01"),
    ),
    package_case(
        "M-DQ-012",
        "DQ-012",
        "même nom de fonction, critique pour une entité et non critique pour une autre",
        lambda p: set_where(p, "B_06.01", "c0010", "F2", "c0030", "FONCTION NON CRITIQUE B"),
    ),
    package_case(
        "M-DQ-013",
        "DQ-013",
        "fonction non critique avec un RTO de 2 heures",
        lambda p: set_where(p, "B_06.01", "c0010", "F3", "c0080", "2"),
    ),
    package_case(
        "M-REL-013",
        "REL-013",
        "service d'une fonction critique absent de B_07.01",
        lambda p: delete_where(p, "B_07.01", c0010="CONTRAT DIRECT EF"),
    ),
    package_case(
        "M-REL-014",
        "REL-014",
        "ligne de B_07.01 dont le type de service n'existe pas en B_02.02",
        lambda p: set_where(p, "B_07.01", "c0010", "CONTRAT PARTAGE", "c0040", "eba_TA:S03"),
        also=("REL-013",),
    ),
    package_case(
        "M-REL-015",
        "REL-015",
        "niveau de dépendance renseigné pour une fonction non critique",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT IG LEVEL 0", "c0180", "eba_ZZ:x795"),
    ),
    package_case(
        "M-REL-016",
        "REL-016",
        "niveau de dépendance vide pour une fonction critique",
        lambda p: set_where(p, "B_02.02", "c0010", "CONTRAT DIRECT EF", "c0180", ""),
    ),
    package_case(
        "M-REL-017",
        "REL-017",
        "service d'une fonction critique sans stratégie de sortie",
        lambda p: set_where(p, "B_07.01", "c0010", "CONTRAT DIRECT EF", "c0080", "eba_BT:x29"),
    ),
    # ------------------------------------------------------------ Sprint 3, lot 5 (chaînes)
    package_case(
        "M-REL-018",
        "REL-018",
        "couple contrat et type de service sans ligne de rang 1",
        lambda p: delete_where(p, "B_05.02", c0010="CONTRAT DIRECT EF", c0050="1"),
    ),
    package_case(
        "M-REL-019",
        "REL-019",
        "rupture de chaîne : un rang 3 devient rang 4",
        lambda p: set_where(p, "B_05.02", "c0030", "529900JULHLZDL9AS417", "c0050", "4"),
    ),
    package_case(
        "M-BUS-018",
        "BUS-018",
        "destinataire du rang 1 différent du prestataire",
        lambda p: set_where(p, "B_05.02", "c0010", "CONTRAT DIRECT EF", "c0060", EF),
    ),
    package_case(
        "M-REL-020",
        "REL-020",
        "chaîne passant par un prestataire intragroupe sans lien en B_02.03",
        lambda p: delete_where(p, "B_02.03"),
        also=("REL-018", "REL-019"),  # the exception of the rank 1 disappears with the link
    ),
    package_case(
        "M-REL-021",
        "REL-021",
        "accord relié en B_02.03 dont tous les prestataires sont intragroupe",
        lambda p: add_row(
            p, "B_02.03", c0010="CONTRAT INTRA GROUPE", c0020="CONTRAT IG LEVEL 0", c0030="true"
        ),
    ),
    package_case(
        "M-BUS-019",
        "BUS-019",
        "prestataire d'une chaîne critique identifié ni par un LEI ni par un EUID",
        lambda p: _critical_without_lei(p),
    ),
    # ------------------------------------------------------------ Sprint 3, lot 6 (listes fermées)
    package_case(
        "M-DAT-033",
        "DAT-033",
        "libellé « High » saisi à la place du code eba_ZZ:x793 (liste L18)",
        lambda p: set_where(p, "B_06.01", "c0010", "F1", "c0100", "High"),
    ),
    package_case(
        "M-DAT-033-HRK",
        "DAT-033",
        "devise HRK, absente de la liste L05 de la taxonomie (décision du PO du 30/10)",
        lambda p: set_where(p, "B_02.01", "c0010", "CONTRAT DIRECT EF", "c0040", "eba_CU:HRK"),
        also=("DQ-015",),
    ),
    package_case(
        "M-DAT-034",
        "DAT-034",
        "personne physique déclarée avec un EUID (décision du PO du 02/11)",
        lambda p: add_row(
            p,
            "B_05.01",
            c0010="FRRCSPARIS.394199723",
            c0020=EUID,
            c0070=NATURAL_PERSON_TYPE,
            c0080="eba_GA:FR",
        ),
    ),
    package_case(
        "M-DAT-035",
        "DAT-035",
        "personne physique déclarée avec un LEI (conseil, décision du PO du 02/11)",
        lambda p: add_row(
            p,
            "B_05.01",
            c0010=LEI_OTHER,
            c0020=LEI,
            c0070=NATURAL_PERSON_TYPE,
            c0080="eba_GA:FR",
        ),
    ),
    package_case(
        "M-REL-007-SOUS-TRAITANT",
        "REL-007",
        "sous-traitant personne morale identifié par un SIREN (contrôle élargi le 02/11)",
        lambda p: add_row(p, "B_05.01", c0010="394199723", c0020=CRN, c0070="eba_CT:x212"),
    ),
)

# Codes qu'un fichier ne peut pas provoquer par mutation simple (cas manuels ou à traiter à part).
MANUAL = {
    "ENG-001": "contrôle interrompu par une erreur interne (non reproductible sur un fichier ; test unitaire)",
    "XML-004": "XML non conforme au schéma de l'enveloppe (aucun XSD déposé dans l'outil)",
    # Contrôles GLEIF (branche feature/gleif-local) : ils comparent le registre à une copie
    # locale du GLEIF, qu'une mutation du golden ne fournit pas. Testés par tests/test_gleif.py
    # avec un extrait du GLEIF fabriqué pour le test.
    "GLF-001": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-002": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-003": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-004": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-005": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-006": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-007": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-008": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-009": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-010": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
    "GLF-011": "contrôle GLEIF : extrait du GLEIF fabriqué pour le test (tests/test_gleif.py)",
}
