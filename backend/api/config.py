# SPDX-License-Identifier: EUPL-1.2
"""Application settings.

Values can be overridden with environment variables prefixed with ``ROI_``
(for example ``ROI_CORS_ORIGINS='["http://localhost:3000"]'``).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "DORA QA"
APP_VERSION = "0.9.0"


class Settings(BaseSettings):
    """Runtime configuration of the API."""

    model_config = SettingsConfigDict(env_prefix="ROI_")

    # Host names accepted in the Host header (red team review S5, PO decision of 30/10): the
    # validator always runs on the user's machine. Any other name is refused (DNS rebinding).
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "backend"]

    # Browser origins allowed to call the API. Local frontend only by default.
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Import limits. A register of 100 MB is already far beyond real cases.
    max_upload_mb: int = 100
    max_uncompressed_mb: int = 500
    max_zip_entries: int = 200
    # Limits of the tables (PO, 07/11/2026, CL-46): characters of a cell, columns of a table,
    # data rows of the whole register.
    max_cell_characters: int = 10_000
    max_columns: int = 200
    max_rows: int = 2_000_000

    # Minutes of inactivity after which the register kept in memory is dropped.
    dataset_ttl_minutes: int = 30

    # Parent folder of the temporary import folders. Defaults to the system one,
    # inside the container. It must never be a mounted volume.
    temp_dir: str | None = None

    # Portable build only (api/portable.py): folder of the built interface, served by the
    # API itself on the same origin. Empty in Docker, where nginx serves the interface.
    static_dir: str | None = None
    # Local copy of the GLEIF data (branch feature/gleif-local). Written by the gleif-updater
    # container in a shared volume, read here only: the backend itself never goes online.
    gleif_enabled: bool = False
    gleif_dir: str = "/data/gleif"


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once per process."""
    return Settings()
