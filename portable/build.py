# SPDX-License-Identifier: EUPL-1.2
"""Build the portable demo ZIP of ROI Quality Engine for the current system.

Run from the repository root, on the target system (Windows, macOS or Linux):

    uv run --project backend --with pyinstaller python portable/build.py

Steps: build the interface (same-origin API), freeze the backend and the launcher with
PyInstaller (one folder), add the user guide, then zip everything into dist-portable/.
"""

import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
OUT = REPO / "dist-portable"
NAME = "ROI-Quality-Engine-DEMO"
SEP = ";" if sys.platform == "win32" else ":"


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, env=env, shell=sys.platform == "win32")


def version() -> str:
    for line in (BACKEND / "api" / "config.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("APP_VERSION"):
            return line.split('"')[1]
    return "dev"


def build_frontend() -> Path:
    import os

    env = dict(os.environ, VITE_API_URL="")  # API on the same origin as the page
    run(["npm", "ci", "--no-audit", "--no-fund"], FRONTEND, env)
    run(["npm", "run", "build"], FRONTEND, env)
    dist = FRONTEND / "dist"
    bundle = "".join(p.read_text(encoding="utf-8") for p in (dist / "assets").glob("*.js"))
    if "localhost:8000" in bundle:
        sys.exit("The interface still calls localhost:8000: VITE_API_URL was not applied.")
    return dist


def freeze(dist: Path) -> Path:
    work = OUT / "build"
    shutil.rmtree(work, ignore_errors=True)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(REPO / "portable" / "launcher.py"),
        "--name",
        NAME,
        "--onedir",
        "--console",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(OUT / "app"),
        "--workpath",
        str(work),
        "--specpath",
        str(work),
        "--paths",
        str(BACKEND),
        "--add-data",
        f"{BACKEND / 'reference'}{SEP}reference",
        "--add-data",
        f"{BACKEND / 'api' / 'static'}{SEP}api/static",
        "--add-data",
        f"{dist}{SEP}frontend",
    ]
    for package in (
        "api",
        "contracts",
        "dataset",
        "import_engine",
        "indicators",
        "reports",
        "rules",
        "scoring",
        "uvicorn",
    ):
        cmd += ["--collect-submodules", package]
    for package in ("polars", "duckdb", "lxml"):
        cmd += ["--collect-all", package]
    run(cmd, REPO)
    return OUT / "app" / NAME


def package(app: Path) -> Path:
    shutil.copy(REPO / "portable" / "LISEZ-MOI-DEMO.txt", app / "LISEZ-MOI-DEMO.txt")
    samples = app / "exemples"
    samples.mkdir(exist_ok=True)
    # Fictitious files only (sample-data/README.md): the golden keeps its official name.
    data = REPO / "sample-data"
    wanted = [*data.glob("*.sample.zip"), *data.glob("*.sample.xml"), *data.glob("529900*.zip")]
    for sample in wanted:
        shutil.copy(sample, samples / sample.name)
    if sys.platform != "win32":
        starter = app / "Lancer-la-demo.command"
        starter.write_text(f'#!/bin/sh\ncd "$(dirname "$0")"\n./{NAME}\n', encoding="utf-8")
        starter.chmod(0o755)

    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    archive = OUT / f"{NAME}-{version()}-{system}-{platform.machine().lower()}.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(app.rglob("*")):
            info = zipfile.ZipInfo.from_file(path, Path(NAME) / path.relative_to(app))
            if path.is_dir():
                zf.writestr(info, "")
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                with path.open("rb") as src:
                    zf.writestr(info, src.read())
    return archive


def main() -> None:
    shutil.rmtree(OUT / "app", ignore_errors=True)
    archive = package(freeze(build_frontend()))
    size = archive.stat().st_size / 1_000_000
    print(f"\nZIP portable de demonstration : {archive} ({size:.0f} Mo)")


if __name__ == "__main__":
    main()
