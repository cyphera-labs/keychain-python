from __future__ import annotations

import base64
import os

from .provider import (
    KeyNotFoundError,
    KeyProvider,
    KeyRecord,
    Status,
)


def _decode_bytes(value: str) -> bytes:
    """Try hex decoding first, then standard base64, then URL-safe base64."""
    # Attempt hex
    try:
        return bytes.fromhex(value)
    except ValueError:
        pass

    # Attempt standard base64
    try:
        return base64.b64decode(value)
    except Exception:
        pass

    # Attempt URL-safe base64
    return base64.urlsafe_b64decode(value)


def _normalize_ref(ref: str) -> str:
    """Uppercase ref and replace '-' and '.' with '_'."""
    return ref.upper().replace("-", "_").replace(".", "_")


class EnvProvider(KeyProvider):
    """Key provider that reads keys from environment variables.

    For a ref of ``customer-primary`` and prefix ``CYPHERA``, the provider
    looks for the environment variable ``CYPHERA_CUSTOMER_PRIMARY_KEY`` (hex
    or base64 encoded) and optionally ``CYPHERA_CUSTOMER_PRIMARY_TWEAK``.

    All keys provided via environment variables are treated as version 1 and
    status ``active``.
    """

    def __init__(self, prefix: str = "CYPHERA") -> None:
        # Strip trailing underscore from prefix for consistent formatting
        self._prefix = prefix.rstrip("_")

    def _env_key(self, ref: str, suffix: str) -> str:
        normalized = _normalize_ref(ref)
        return f"{self._prefix}_{normalized}_{suffix}"

    def _load(self, ref: str) -> KeyRecord:
        key_var = self._env_key(ref, "KEY")
        raw = os.environ.get(key_var)
        if raw is None:
            raise KeyNotFoundError(ref)

        material = _decode_bytes(raw)

        tweak: bytes | None = None
        tweak_var = self._env_key(ref, "TWEAK")
        raw_tweak = os.environ.get(tweak_var)
        if raw_tweak is not None:
            tweak = _decode_bytes(raw_tweak)

        return KeyRecord(
            ref=ref,
            version=1,
            status=Status.ACTIVE,
            material=material,
            tweak=tweak,
        )

    def resolve(self, ref: str) -> KeyRecord:
        """Return the (sole) active key for the given ref from env vars."""
        return self._load(ref)

    def resolve_version(self, ref: str, version: int) -> KeyRecord:
        """Return the key for the given ref and version.

        Only version 1 exists for env-var-backed keys; any other version raises
        KeyNotFoundError.
        """
        if version != 1:
            raise KeyNotFoundError(ref, version)
        return self._load(ref)
