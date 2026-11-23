# SPDX-License-Identifier: EUPL-1.2
"""In-memory storage of the register being analysed.

Confidentiality rules applied here:
- one register at a time: a new import replaces the previous one;
- nothing is written to disk;
- the register is dropped after a period of inactivity, and on shutdown.
"""

import threading
import time

from contracts.dataset import RoIDataset


class DatasetStore:
    def __init__(self, ttl_seconds: int = 1800) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._import_id: str | None = None
        self._dataset: RoIDataset | None = None
        self._expires_at = 0.0

    def put(self, import_id: str, dataset: RoIDataset) -> None:
        """Keep a dataset, replacing whatever was stored before."""
        with self._lock:
            self._import_id = import_id
            self._dataset = dataset
            self._expires_at = time.monotonic() + self._ttl

    def get(self, import_id: str) -> RoIDataset | None:
        """Return the dataset of an import, or None if it is unknown or expired."""
        with self._lock:
            self._drop_if_expired()
            if self._import_id != import_id:
                return None
            self._expires_at = time.monotonic() + self._ttl
            return self._dataset

    def purge(self) -> None:
        with self._lock:
            self._import_id = None
            self._dataset = None

    def expire(self) -> bool:
        """Drop the dataset if its time is over. Returns True when something was dropped.

        Called periodically by the API, so that an unread register does not stay in
        memory until the next import.
        """
        with self._lock:
            had = self._dataset is not None
            self._drop_if_expired()
            return had and self._dataset is None

    def _drop_if_expired(self) -> None:
        if self._dataset is not None and time.monotonic() > self._expires_at:
            self._import_id = None
            self._dataset = None
