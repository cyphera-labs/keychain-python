from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .provider import (
    KeyDisabledError,
    KeyNotFoundError,
    KeyProvider,
    KeyRecord,
    NoActiveKeyError,
    Status,
)


def _decode_bytes(value: str) -> bytes:
    """Try hex decoding first, then standard base64, then URL-safe base64."""
    try:
        return bytes.fromhex(value)
    except ValueError:
        pass

    try:
        return base64.b64decode(value)
    except Exception:
        pass

    return base64.urlsafe_b64decode(value)


def _parse_record(obj: dict[str, Any]) -> KeyRecord:
    ref: str = obj["ref"]
    version: int = int(obj["version"])
    status = Status(obj["status"])
    algorithm: str = obj.get("algorithm", "adf1")

    material = _decode_bytes(obj["material"])

    tweak: Optional[bytes] = None
    raw_tweak = obj.get("tweak")
    if raw_tweak:
        tweak = _decode_bytes(raw_tweak)

    metadata: dict[str, str] = obj.get("metadata", {})

    created_at: Optional[datetime] = None
    raw_created = obj.get("created_at")
    if raw_created:
        created_at = datetime.fromisoformat(raw_created)

    return KeyRecord(
        ref=ref,
        version=version,
        status=status,
        algorithm=algorithm,
        material=material,
        tweak=tweak,
        metadata=metadata,
        created_at=created_at,
    )


class FileProvider(KeyProvider):
    """Key provider that loads keys from a local JSON file.

    The file must have the structure::

        {
            "keys": [
                {
                    "ref": "customer-primary",
                    "version": 1,
                    "status": "active",
                    "algorithm": "adf1",
                    "material": "<hex or base64>",
                    "tweak": "<hex or base64>",
                    "metadata": {},
                    "created_at": "2024-01-01T00:00:00"
                }
            ]
        }

    The file is read once at construction time. The provider is naturally
    thread-safe because the internal store is read-only after initialization.
    """

    def __init__(self, path: str | Path) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        # Build store: dict[ref -> list[KeyRecord]] sorted descending by version
        self._store: dict[str, list[KeyRecord]] = {}
        for obj in data.get("keys", []):
            record = _parse_record(obj)
            versions = self._store.setdefault(record.ref, [])
            versions.append(record)

        for versions in self._store.values():
            versions.sort(key=lambda r: r.version, reverse=True)

    def resolve(self, ref: str) -> KeyRecord:
        """Return the highest-version active record for the given ref."""
        versions = self._store.get(ref)
        if not versions:
            raise KeyNotFoundError(ref)

        for record in versions:
            if record.status == Status.ACTIVE:
                return record

        raise NoActiveKeyError(ref)

    def resolve_version(self, ref: str, version: int) -> KeyRecord:
        """Return a specific version of the key for the given ref."""
        versions = self._store.get(ref)
        if not versions:
            raise KeyNotFoundError(ref, version)

        for record in versions:
            if record.version == version:
                if record.status == Status.DISABLED:
                    raise KeyDisabledError(ref, version)
                return record

        raise KeyNotFoundError(ref, version)
