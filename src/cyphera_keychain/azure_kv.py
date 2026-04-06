"""Azure Key Vault key provider."""
from __future__ import annotations

import os
import threading
from typing import Optional

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, KeyWrapAlgorithm

from .provider import KeyNotFoundError, KeyProvider, KeyRecord, Status


class AzureKvProvider(KeyProvider):
    """Key provider backed by Azure Key Vault.

    Generates a random AES-256 data key, wraps it with an Azure Key Vault RSA
    key (RSA-OAEP), and caches the plaintext for the lifetime of the provider.

    Args:
        vault_url: Azure Key Vault URL, e.g. ``https://my-vault.vault.azure.net``.
        key_name: Name of the RSA key in the vault used for wrapping.
        credential: Azure credential; defaults to ``DefaultAzureCredential``.
        key_client: Optional pre-constructed KeyClient (for testing).
    """

    def __init__(
        self,
        vault_url: str,
        key_name: str,
        *,
        credential=None,
        key_client: Optional[KeyClient] = None,
    ) -> None:
        self._vault_url = vault_url
        self._key_name = key_name
        self._credential = credential or DefaultAzureCredential()
        self._key_client = key_client or KeyClient(vault_url=vault_url, credential=self._credential)
        self._plaintext: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def _get_crypto_client(self) -> CryptographyClient:
        key = self._key_client.get_key(self._key_name)
        return CryptographyClient(key, credential=self._credential)

    def _wrap_new_key(self) -> bytes:
        plaintext = os.urandom(32)
        crypto = self._get_crypto_client()
        crypto.wrap_key(KeyWrapAlgorithm.rsa_oaep, plaintext)
        return plaintext

    def resolve(self, ref: str) -> KeyRecord:
        with self._lock:
            if ref not in self._plaintext:
                try:
                    self._plaintext[ref] = self._wrap_new_key()
                except (HttpResponseError, ResourceNotFoundError) as exc:
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
