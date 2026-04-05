from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Status(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


@dataclass(frozen=True)
class KeyRecord:
    ref: str
    version: int
    status: Status
    algorithm: str = "adf1"
    material: bytes = b""
    tweak: Optional[bytes] = None
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: Optional[datetime] = None


class KeyNotFoundError(Exception):
    def __init__(self, ref: str, version: Optional[int] = None) -> None:
        self.ref = ref
        self.version = version
        if version is not None:
            super().__init__(f"key not found: ref={ref!r} version={version}")
        else:
            super().__init__(f"key not found: ref={ref!r}")


class KeyDisabledError(Exception):
    def __init__(self, ref: str, version: int) -> None:
        self.ref = ref
        self.version = version
        super().__init__(f"key is disabled: ref={ref!r} version={version}")


class NoActiveKeyError(Exception):
    def __init__(self, ref: str) -> None:
        self.ref = ref
        super().__init__(f"no active key found: ref={ref!r}")


class KeyProvider(ABC):
    @abstractmethod
    def resolve(self, ref: str) -> KeyRecord:
        """Return the highest-version active record for encryption."""
        ...

    @abstractmethod
    def resolve_version(self, ref: str, version: int) -> KeyRecord:
        """Return a specific version of a key record for decryption."""
        ...
