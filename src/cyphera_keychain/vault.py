"""HashiCorp Vault key provider."""
from __future__ import annotations

from typing import Optional

import hvac
from hvac.exceptions import InvalidPath, VaultError

from .provider import (
    KeyDisabledError,
    KeyNotFoundError,
    KeyProvider,
    KeyRecord,
    NoActiveKeyError,
    Status,
)


def _decode_bytes(value: str) -> bytes:
    """Decode hex or base64 encoded bytes."""
    import binascii, base64
    stripped = value.strip()
    if len(stripped) % 2 == 0:
        try:
            return bytes.fromhex(stripped)
        except ValueError:
            pass
    try:
        return base64.b64decode(stripped)
    except Exception:
        return base64.urlsafe_b64decode(stripped + "==")


class VaultProvider(KeyProvider):
    """Key provider backed by HashiCorp Vault KV v2 secrets engine.

    Key records are stored at ``{mount}/{ref}`` as secret data fields.

    Single-version secret data format::

        {
          "version": "1",
          "status": "active",
          "algorithm": "adf1",
          "material": "<hex or base64>"
        }

    Multi-version: store a ``versions`` JSON array as a field (advanced use).

    Args:
        url: Vault server URL.
        token: Vault root/service token.
        mount: KV v2 mount path (default: ``secret``).
        client: Optional pre-constructed hvac.Client (for testing).
    """

    def __init__(
        self,
        url: str = "http://127.0.0.1:8200",
        token: Optional[str] = None,
        *,
        mount: str = "secret",
        client: Optional[hvac.Client] = None,
    ) -> None:
        self._mount = mount
        self._client = client or hvac.Client(url=url, token=token)

    def _read_data(self, ref: str) -> dict:
        try:
            secret = self._client.secrets.kv.v2.read_secret_version(
                path=ref,
                mount_point=self._mount,
                raise_on_deleted_version=True,
            )
            return secret["data"]["data"]
        except InvalidPath:
            raise KeyNotFoundError(ref)
        except (VaultError, KeyError) as exc:
            raise KeyNotFoundError(ref) from exc

    def _parse_one(self, ref: str, data: dict) -> KeyRecord:
        raw = data.get("material", "")
        material = _decode_bytes(raw) if raw else b""
        tweak_raw = data.get("tweak")
        tweak = _decode_bytes(tweak_raw) if tweak_raw else None
        return KeyRecord(
            ref=data.get("ref", ref),
            version=int(data.get("version", 1)),
            status=Status(data.get("status", "active")),
            algorithm=data.get("algorithm", "adf1"),
            material=material,
            tweak=tweak,
            metadata=dict(data.get("metadata") or {}),
        )

    def _parse_records(self, ref: str, data: dict) -> list[KeyRecord]:
        if "versions" in data:
            import json
            versions = data["versions"]
            if isinstance(versions, str):
                versions = json.loads(versions)
            return [self._parse_one(ref, v) for v in versions]
        return [self._parse_one(ref, data)]

    def resolve(self, ref: str) -> KeyRecord:
        data = self._read_data(ref)
        records = self._parse_records(ref, data)
        active = [r for r in records if r.status == Status.ACTIVE]
        if not active:
            raise NoActiveKeyError(ref)
        return max(active, key=lambda r: r.version)

    def resolve_version(self, ref: str, version: int) -> KeyRecord:
        data = self._read_data(ref)
        records = self._parse_records(ref, data)
        for record in records:
            if record.version == version:
                if record.status == Status.DISABLED:
                    raise KeyDisabledError(ref, version)
                return record
        raise KeyNotFoundError(ref, version)
