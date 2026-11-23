# SPDX-License-Identifier: EUPL-1.2
"""Launcher of the portable build of DORA QA.

Starts the API on 127.0.0.1 only, serving the interface itself (api/portable.py), opens the
default browser and runs until the window is closed or Ctrl+C is pressed.

Two versions, chosen at build time (file ``edition.txt`` of the bundle, written by build.py) or by
the variable ``DORA_QA_EDITION`` (offline | online):

- offline: no network code at all; the GLEIF checks are left out and the screen says so;
- online: before any register is accepted, a separate process (this launcher started again with
  ``--gleif-update``) downloads the public GLEIF copy into the user cache folder, then exits.
  While it runs, the page shows a waiting screen and imports are refused; a watchdog kills it if
  it outlives ``gleif.updater.MAX_SECONDS``. Once it has exited, nothing goes online any more.

Nothing about a register is written outside the system temporary folder, and the temporary import
folders are purged on exit. The online version keeps the public GLEIF copy in the user cache.

Frozen by PyInstaller (portable/build.py); can also run from the repository for a quick check:

    cd backend && uv run python ../portable/launcher.py
"""

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PREFERRED_PORT = 8765
EDITION_FILE = "edition.txt"
EDITIONS = ("offline", "online")
UPDATE_FLAG = "--gleif-update"
BANNER = r"""
============================================================================
  DORA QA - DORA Register Quality Analyst
  Analyse locale : le registre ne quitte pas ce poste. Local analysis only.
  Outil fourni "en l'etat", sans garantie / provided "as is", no warranty.
============================================================================
"""


def bundle_root() -> Path:
    """Folder holding the backend packages and the built interface."""
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen)
    return Path(__file__).resolve().parent.parent / "backend"


def frontend_dir(root: Path) -> Path:
    if getattr(sys, "_MEIPASS", None):
        return root / "frontend"
    return root.parent / "frontend" / "dist"


def edition(root: Path) -> str:
    """offline (default) or online."""
    value = os.environ.get("DORA_QA_EDITION", "").strip().lower()
    if not value and (root / EDITION_FILE).is_file():
        value = (root / EDITION_FILE).read_text(encoding="utf-8").strip().lower()
    value = value or "offline"
    if value not in EDITIONS:
        sys.exit(f"Edition inconnue / unknown edition: {value}")
    return value


def gleif_dir() -> Path:
    """User cache folder of the GLEIF copy: public data only, never a register."""
    home = Path.home()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local") / "DORA-QA"
    elif sys.platform == "darwin":
        base = home / "Library" / "Caches" / "DORA-QA"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache") / "dora-qa"
    return base / "gleif"


def update_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, UPDATE_FLAG]
    return [sys.executable, str(Path(__file__).resolve()), UPDATE_FLAG]


def start_gleif_update(folder: Path) -> None:
    """Run the update in its own process and watch it (online version only)."""
    from contracts.gleif import GleifState
    from gleif.layout import installed_manifest
    from gleif.status import write_status
    from gleif.updater import MAX_SECONDS

    folder.mkdir(parents=True, exist_ok=True)
    # Closed from the very first request: a status left READY by the last run must not let a
    # register in before the update process has started.
    write_status(folder, GleifState.UPDATING, received_bytes=0, total_bytes=0)
    print("  Mise a jour de la copie GLEIF en ligne : aucun registre accepte pendant ce temps.")
    print("  Updating the GLEIF copy online: no register is accepted meanwhile.")
    process = subprocess.Popen(update_command(), env=dict(os.environ, ROI_GLEIF_DIR=str(folder)))

    def watch() -> None:
        error = None
        try:
            process.wait(timeout=MAX_SECONDS + 30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            error = "too_long"
        if error:
            state = GleifState.READY if installed_manifest(folder) else GleifState.UNAVAILABLE
            write_status(folder, state, last_error=error)
        manifest = installed_manifest(folder)
        if manifest:
            day = str(manifest.get("content_date", ""))[:10]
            print(f"  Copie GLEIF du {day} prete. / GLEIF copy of {day} ready.")
        else:
            print("  Copie GLEIF indisponible : controles GLEIF non evalues.")
            print("  GLEIF copy unavailable: GLEIF checks not evaluated.")
        print("  Plus aucune connexion. / No connection from now on.")

    threading.Thread(target=watch, daemon=True, name="gleif-watchdog").start()


def free_port() -> int:
    """The preferred port if free, otherwise any free port, on 127.0.0.1 only."""
    for port in (PREFERRED_PORT, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return int(sock.getsockname()[1])
    raise RuntimeError("No free local port")


def open_browser_when_ready(url: str) -> None:
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    print(f"\n  Interface : {url}")
    print("  (Fermez cette fenetre pour arreter / close this window to stop)\n")
    # DORA_QA_NO_BROWSER=1: automated checks of the build (CI), nobody to look at the page.
    if not os.environ.get("DORA_QA_NO_BROWSER"):
        webbrowser.open(url)


def main() -> None:
    # The console is the only trace the user sees: print without delay.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
    if UPDATE_FLAG in sys.argv[1:]:
        # Child process of the online version: download the GLEIF copy, then exit.
        sys.path.insert(0, str(bundle_root()))
        try:
            from gleif.updater import main as update
        except ImportError:
            sys.exit("Version hors ligne : aucune mise a jour GLEIF. / Offline version: no update.")
        sys.exit(update())
    print(BANNER)
    if sys.version_info[:2] != (3, 13):
        sys.exit("Python 3.13 requis / required (installer Python 3.13 depuis python.org).")
    root = bundle_root()
    static = frontend_dir(root)
    if not (static / "index.html").is_file():
        sys.exit(f"Interface introuvable / interface not found: {static}")

    # Read by api.config when api.main is imported: set before the import.
    os.environ["ROI_STATIC_DIR"] = str(static)
    sys.path.insert(0, str(root))
    version = edition(root)
    print(f"  Version : {'en ligne / online' if version == 'online' else 'hors ligne / offline'}")
    if version == "online":
        folder = gleif_dir()
        os.environ["ROI_GLEIF_ENABLED"] = "true"
        os.environ["ROI_GLEIF_DIR"] = str(folder)
        start_gleif_update(folder)
    else:
        os.environ["ROI_GLEIF_ENABLED"] = "false"

    import uvicorn

    from api.main import app

    port = free_port()
    url = f"http://127.0.0.1:{port}"
    print("  Demarrage... / Starting...")
    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()
    # 127.0.0.1 only: the tool is never reachable from the network.
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
