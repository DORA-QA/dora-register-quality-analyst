# SPDX-License-Identifier: EUPL-1.2
"""La mise en forme des archives de recette (CL-18 / A2) ne change pas le verdict du moteur."""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.cases.export_mutations import PACKAGE_PREFIXES
from tests.cases.mutations import MUTATIONS
from tests.cases.zip_layout import with_directories
from tests.factories import CLIENT_HEADERS


def test_directories_are_added_and_paths_kept() -> None:
    src = io.BytesIO()
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("root/META-INF/reportPackage.json", b"{}")
        z.writestr("root/reports/b_01.01.csv", b"a\n")
    out = zipfile.ZipFile(io.BytesIO(with_directories(src.getvalue())))
    names = out.namelist()
    assert {"root/", "root/META-INF/", "root/reports/"} <= set(names)
    assert out.read("root/reports/b_01.01.csv") == b"a\n"
    assert all("\\" not in n for n in names)


def test_unreadable_archive_is_left_untouched() -> None:
    broken = b"PK not really a zip"
    assert with_directories(broken) == broken


PACKAGE_CASES = [m for m in MUTATIONS if m.code.startswith(PACKAGE_PREFIXES)]


@pytest.fixture(scope="module")
def client():
    with TestClient(app, headers=CLIENT_HEADERS) as c:
        yield c


@pytest.mark.parametrize("mutation", PACKAGE_CASES, ids=lambda m: m.case)
def test_layout_does_not_change_verdict(client, mutation) -> None:
    name, content = mutation.apply(_golden())
    if not name.endswith(".zip"):
        pytest.skip("not an archive")
    codes = lambda data: sorted(  # noqa: E731
        m["code"]
        for m in client.post("/api/import", files={"file": (name, data)}).json().get("messages", [])
    )
    assert codes(content) == codes(with_directories(content))


def _golden():
    from tests.cases.golden import load_golden

    return load_golden()
