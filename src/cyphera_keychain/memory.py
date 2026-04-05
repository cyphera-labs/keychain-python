from __future__ import annotations

import threading
from typing import Optional

from .provider import (
    KeyDisabledError,
    KeyNotFoundError,
    KeyProvider,
    KeyRecord,
    NoActiveKeyError,
    Status,
)


class MemoryProvider(KeyProvider):
    """In-memory key provider, thread-safe via RLock.

    Accepts an arbitrary number of KeyRecord positional arguments at
    construction time, plus additional records via add().
    """

    def __init__(self, *records: KeyRecord) -> None:
        self._lock = threading.RLock()
        # dict[ref -> list[KeyRecord]] sorted descending by version
        self._store: dict[str, list[KeyRecord]] = {}
        for record in records:
            self._insert(record)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _insert(self, record: KeyRecord) -> None:
        """Insert a record and keep the list sorted descending by version."""
        versions = self._store.setdefault(record.ref, [])
        versions.append(record)
        versions.sort(key=lambda r: r.version, reverse=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, record: KeyRecord) -> None:
        """Add a KeyRecord to the in-memory store."""
        with self._lock:
            self._insert(record)

    def resolve(self, ref: str) -> KeyRecord:
        """Return the highest-version active record for the given ref."""
        with self._lock:
            versions = self._store.get(ref)
            if not versions:
                raise KeyNotFoundError(ref)

            for record in versions:  # already sorted descending
                if record.status == Status.ACTIVE:
                    return record

            # Records exist but none are active
            raise NoActiveKeyError(ref)

    def resolve_version(self, ref: str, version: int) -> KeyRecord:
        """Return a specific version of the key for the given ref."""
        with self._lock:
            versions = self._store.get(ref)
            if not versions:
                raise KeyNotFoundError(ref, version)

            for record in versions:
                if record.version == version:
                    if record.status == Status.DISABLED:
                        raise KeyDisabledError(ref, version)
                    return record

            raise KeyNotFoundError(ref, version)
