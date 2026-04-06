"""AWS KMS key provider."""
from __future__ import annotations

import threading
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from .provider import KeyNotFoundError, KeyProvider, KeyRecord, Status


class AwsKmsProvider(KeyProvider):
    """Key provider backed by AWS KMS data-key generation.

    Each resolved ref is backed by an AES-256 data key generated via the
    configured KMS master key. The plaintext data key is cached in memory
    for the lifetime of the provider.

    Args:
        key_id: KMS key ARN, key ID, or alias.
        region: AWS region name.
        endpoint_url: Optional endpoint URL override (e.g. for LocalStack).
    """

    def __init__(
        self,
        key_id: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
    ) -> None:
        self._key_id = key_id
        self._client = boto3.client("kms", region_name=region, endpoint_url=endpoint_url)
        self._cache: dict[str, KeyRecord] = {}
        self._lock = threading.Lock()

    def _generate(self, ref: str) -> KeyRecord:
        try:
            resp = self._client.generate_data_key(
                KeyId=self._key_id,
                KeySpec="AES_256",
                EncryptionContext={"cyphera:ref": ref},
            )
        except ClientError as exc:
            raise KeyNotFoundError(ref) from exc
        return KeyRecord(
            ref=ref,
            version=1,
            status=Status.ACTIVE,
            algorithm="aes256",
            material=bytes(resp["Plaintext"]),
        )

    def resolve(self, ref: str) -> KeyRecord:
        with self._lock:
            if ref not in self._cache:
                self._cache[ref] = self._generate(ref)
            return self._cache[ref]

    def resolve_version(self, ref: str, version: int) -> KeyRecord:
        if version != 1:
            raise KeyNotFoundError(ref, version)
        return self.resolve(ref)
