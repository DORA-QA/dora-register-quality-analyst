# SPDX-License-Identifier: EUPL-1.2
"""Launcher of the portable demo build of ROI Quality Engine.

Starts the API on 127.0.0.1 only, serving the interface itself (api/portable.py), opens the
default browser and runs until the window is closed or Ctrl+C is pressed. Nothing is written
outside the system temporary folder, and the temporary import folders are purged on exit.

Frozen by PyInstaller (portable/build.py); can also run from the repository for a quick check:

    cd backend && uv run python ../portable/launcher.py
"""

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PREFERRED_PORT = 8765
BANNER = r"""
============================================================================
  ROI Quality Engine - VERSION DE DEMONSTRATION / DEMO VERSION
  NE PAS UTILISER EN PRODUCTION - NOT FOR PRODUCTION USE
  Aucune donnee reelle ou confidentielle. No real or confidential data.
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
    webbrowser.open(url)


def main() -> None:
    # The console is the only trace the user sees: print without delay.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
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

    import uvicorn

    from api.main import app

    port = free_port()
    url = f"http://127.0.0.1:{port}"
    print("  Demarrage... / Starting...")
    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()
    # 127.0.0.1 only: the demo is never reachable from the network.
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
