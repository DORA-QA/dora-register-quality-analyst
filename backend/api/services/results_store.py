# SPDX-License-Identifier: EUPL-1.2
"""Results of the last analyses, kept in memory (red team RT-13; decision A5 of the PO, 02/11/2026).

Until 0.8.2 a single outcome was kept: a second tab importing a register erased the first one,
whose change of language then answered 404. The results are now kept by import identifier:

- at most ``MAX_RESULTS`` analyses (2): a third import drops the oldest;
- each one is dropped after ``ttl_seconds`` without being read (30 minutes by default);
- everything is dropped on shutdown, and an analysis on request (``DELETE /api/import/{id}``).

Only the findings are kept, never the register itself: the dataset follows its own rules
(``dataset.store``, one register at a time). Nothing is written to disk.
"""

import threading
import time
from collections import OrderedDict

MAX_RESULTS = 2


class ResultsStore[T]:
    def __init__(self, ttl_seconds: int = 1800, max_results: int = MAX_RESULTS) -> None:
        self._ttl = ttl_seconds
        self._max = max_results
        self._lock = threading.Lock()
        self._items: OrderedDict[str, tuple[T, float]] = OrderedDict()

    def put(self, import_id: str, result: T) -> None:
        """Keep a result; the oldest ones go beyond ``max_results``."""
        with self._lock:
            self._drop_expired()
            self._items[import_id] = (result, time.monotonic() + self._ttl)
            self._items.move_to_end(import_id)
            while len(self._items) > self._max:
                self._items.popitem(last=False)

    def get(self, import_id: str) -> T | None:
        """The result of an import, or None when unknown or expired. Reading it extends its life."""
        with self._lock:
            self._drop_expired()
            entry = self._items.get(import_id)
            if entry is None:
                return None
            self._items[import_id] = (entry[0], time.monotonic() + self._ttl)
            return entry[0]

    def delete(self, import_id: str) -> bool:
        with self._lock:
            return self._items.pop(import_id, None) is not None

    def expire(self) -> None:
        with self._lock:
            self._drop_expired()

    def purge(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            self._drop_expired()
            return len(self._items)

    def _drop_expired(self) -> None:
        now = time.monotonic()
        for key in [k for k, (_, expires) in self._items.items() if now > expires]:
            del self._items[key]
