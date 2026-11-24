# SPDX-License-Identifier: EUPL-1.2
"""Single-process mode used by the portable build (ZIP for Windows and macOS).

In Docker, nginx serves the interface and relays the API. In the portable ZIP there is no
nginx: the API serves the built interface itself, on the same origin, with the security headers
of docker/nginx.conf. Enabled only when ``ROI_STATIC_DIR`` points to a Vite build.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

# Same policy as docker/nginx.conf, with the API on the same origin ('self').
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
    "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
)

# Paths answered by the API itself; everything else is the interface.
API_PREFIXES = ("/api", "/health", "/docs", "/openapi.json", "/static")


def setup_portable_frontend(app: FastAPI, static_dir: str) -> None:
    """Serve the built interface on ``/`` and add the browser security headers."""
    root = Path(static_dir)
    if not (root / "index.html").is_file():
        raise RuntimeError(f"ROI_STATIC_DIR has no index.html: {root}")

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        path = request.url.path
        if path.startswith(API_PREFIXES):
            # Answers change during a session (GLEIF status, analyses): never from a cache.
            response.headers.setdefault("Cache-Control", "no-store")
        else:
            response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
            # Vite puts a content hash in asset names: they never change. The page itself must
            # be checked at every start, or the browser may show the interface of an older
            # version of DORA QA used before on the same address.
            immutable = path.startswith("/assets/")
            response.headers.setdefault(
                "Cache-Control", "public, max-age=31536000, immutable" if immutable else "no-cache"
            )
        return response

    # Mounted last: the API routes keep priority over the files.
    app.mount("/", StaticFiles(directory=root, html=True), name="frontend")
