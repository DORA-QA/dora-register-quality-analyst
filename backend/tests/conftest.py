# SPDX-License-Identifier: EUPL-1.2
# ruff: noqa: E402 - the environment must be set before the application is imported
"""Shared fixtures."""

import os

# The test client calls the API as "testserver": accepted for the tests only (review S5).
# Set before the application is imported, since its settings are read once.
os.environ.setdefault("ROI_ALLOWED_HOSTS", '["localhost", "127.0.0.1", "backend", "testserver"]')

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests import factories
from tests.factories import CLIENT_HEADERS


@pytest.fixture
def client() -> Iterator[TestClient]:
    """API client with the application started (lifespan executed)."""
    with TestClient(app, headers=CLIENT_HEADERS) as test_client:
        yield test_client


@pytest.fixture
def write(tmp_path: Path):
    """Write bytes to a temporary file and return its path as text."""

    def _write(name: str, content: bytes) -> str:
        path = tmp_path / name
        path.write_bytes(content)
        return str(path)

    return _write


@pytest.fixture
def valid_zip(write) -> str:
    return write(f"{factories.PACKAGE_NAME}.zip", factories.build_zip())


def codes(messages) -> list[str]:
    return [message.code for message in messages]
