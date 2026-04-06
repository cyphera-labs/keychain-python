"""GCP Cloud KMS key provider."""
from __future__ import annotations

import os
import threading
from typing import Optional

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import kms as gcp_kms

from .provider import KeyNotFoundError, KeyProvider, KeyRecord, Status


class GcpKmsProvider(KeyProvider):
    """Key provider backed by GCP Cloud KMS.

    Generates a random AES-256 data key, wraps it with a GCP Cloud KMS
    symmetric key, and caches the plaintext for the lifetime of the provider.

    Args:
        key_name: Fully-qualified KMS CryptoKey name:
            ``projects/{p}/locations/{l}/keyRings/{r}/cryptoKeys/{k}``
        client: Optional pre-constructed KMS client (for testing).
    """

    def __init__(
        self,
        key_name: str,
        *,
        client: Optional[gcp_kms.KeyManagementServiceClient] = None,
    ) -> None:
        self._key_name = key_name
        self._client = client or gcp_kms.KeyManagementServiceClient()
        self._plaintext: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def _wrap_new_key(self, ref: str) -> bytes:
        plaintext = os.urandom(32)
        self._client.encrypt(
            request={
                "name": self._key_name,
                "plaintext": plaintext,
                "additional_authenticated_data": ref.encode(),
            }
        )
        return plaintext

    def resolve(self, ref: str) -> KeyRecord:
        with self._lock:
            if ref not in self._plaintext:
                try:
                    self._plaintext[ref] = self._wrap_new_key(ref)
                except GoogleAPICallError as exc:
                    raise KeyNotFoundError(ref) from exc
            return KeyRecord(
                ref=ref,
                version=1,
                status=Status.ACTIVE,
                algorithm="aes256",
                material=self._plaintext[ref],
            )

    def resolve_version(self, ref: str, version: int) -> KeyRecord:
        if version != 1:
            raise KeyNotFoundError(ref, version)
        return self.resolve(ref)
