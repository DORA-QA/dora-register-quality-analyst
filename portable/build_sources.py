# SPDX-License-Identifier: EUPL-1.2
"""Build the "sources" demo ZIP: run ROI Quality Engine from VS Code with a signed Python.

For workstations that block unsigned programs (the PyInstaller ZIP) but allow Python and
VS Code. Nothing is frozen: the ZIP holds the backend sources, the built interface, the
Python libraries as wheels for this system (no access to PyPI needed) and VS Code tasks.

Run from the repository root, on the target system (Windows for a Windows ZIP):

    uv run --project backend python portable/build_sources.py
"""

import os
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
NAME = "ROI-Quality-Engine-DEMO-sources"
WIN = sys.platform == "win32"

# Backend folders needed at run time (tests and tools stay out).
BACKEND_PARTS = [
    "api",
    "contracts",
    "dataset",
    "import_engine",
    "indicators",
    "reference",
    "reports",
    "rules",
    "scoring",
]


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, env=env, shell=WIN)


def version() -> str:
    for line in (BACKEND / "api" / "config.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("APP_VERSION"):
            return line.split('"')[1]
    return "dev"


def build_frontend(target: Path) -> None:
    env = dict(os.environ, VITE_API_URL="")  # API on the same origin as the page
    run(["npm", "ci", "--no-audit", "--no-fund"], FRONTEND, env)
    run(["npm", "run", "build"], FRONTEND, env)
    dist = FRONTEND / "dist"
    bundle = "".join(p.read_text(encoding="utf-8") for p in (dist / "assets").glob("*.js"))
    if "localhost:8000" in bundle:
        sys.exit("The interface still calls localhost:8000: VITE_API_URL was not applied.")
    shutil.copytree(dist, target / "frontend" / "dist")


def copy_backend(target: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".mypy_cache", ".ruff_cache")
    for part in BACKEND_PARTS:
        shutil.copytree(BACKEND / part, target / "backend" / part, ignore=ignore)
    shutil.copy(REPO / "portable" / "launcher.py", target / "portable" / "launcher.py")


def wheels(target: Path) -> None:
    requirements = target / "requirements.txt"
    run(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            "--project",
            str(BACKEND),
            "--format",
            "requirements-txt",
            "-o",
            str(requirements),
        ],
        REPO,
    )
    # Wheels for this system and this Python: the demo workstation installs offline.
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--dest",
            str(target / "wheels"),
            "-r",
            str(requirements),
        ],
        REPO,
    )


def extras(target: Path) -> None:
    shutil.copytree(REPO / "portable" / "vscode", target / ".vscode")
    shutil.copy(REPO / "portable" / "LISEZ-MOI-SOURCES.txt", target / "LISEZ-MOI-DEMO.txt")
    samples = target / "exemples"
    samples.mkdir()
    data = REPO / "sample-data"
    wanted = [*data.glob("*.sample.zip"), *data.glob("*.sample.xml"), *data.glob("529900*.zip")]
    for sample in wanted:
        shutil.copy(sample, samples / sample.name)


def archive(target: Path) -> Path:
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    py = f"py{sys.version_info.major}{sys.version_info.minor}"
    path = OUT / f"{NAME}-{version()}-{system}-{platform.machine().lower()}-{py}.zip"
    path.unlink(missing_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(target.rglob("*")):
            if item.is_file():
                zf.write(item, Path(NAME) / item.relative_to(target))
    return path


def main() -> None:
    target = OUT / "sources" / NAME
    shutil.rmtree(target.parent, ignore_errors=True)
    (target / "portable").mkdir(parents=True)
    copy_backend(target)
    build_frontend(target)
    wheels(target)
    extras(target)
    path = archive(target)
    print(f"\nZIP sources de demonstration : {path} ({path.stat().st_size / 1e6:.0f} Mo)")


if __name__ == "__main__":
    main()
