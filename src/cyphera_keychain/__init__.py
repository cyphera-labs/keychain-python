from __future__ import annotations

from .provider import (
    KeyDisabledError,
    KeyNotFoundError,
    KeyProvider,
    KeyRecord,
    NoActiveKeyError,
    Status,
)
from .memory import MemoryProvider
from .env import EnvProvider
from .file import FileProvider
from .aws_kms import AwsKmsProvider
from .gcp_kms import GcpKmsProvider
from .azure_kv import AzureKvProvider
from .vault import VaultProvider

__all__ = [
    "KeyProvider",
    "KeyRecord",
    "Status",
    "KeyNotFoundError",
    "KeyDisabledError",
    "NoActiveKeyError",
    "MemoryProvider",
    "EnvProvider",
    "FileProvider",
    "AwsKmsProvider",
    "GcpKmsProvider",
    "AzureKvProvider",
    "VaultProvider",
    "resolve",
]


def resolve(source: str, config: dict) -> bytes:
    """Bridge resolver for Cyphera SDK config-driven key sources.

    Called by the SDK when cyphera.json has "source" set to a cloud provider.
    Returns raw key bytes.
    """
    import os

    ref = config.get("ref") or config.get("path") or config.get("arn") or config.get("key") or "default"

    if source == "vault":
        provider = VaultProvider(
            url=config.get("addr") or os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200"),
            token=config.get("token") or os.environ.get("VAULT_TOKEN"),
            mount=config.get("mount", "secret"),
        )
    elif source == "aws-kms":
        provider = AwsKmsProvider(
            key_id=config.get("arn", ""),
            region=config.get("region") or os.environ.get("AWS_REGION", "us-east-1"),
            endpoint_url=config.get("endpoint"),
        )
    elif source == "gcp-kms":
        provider = GcpKmsProvider(
            key_name=config.get("resource", ""),
        )
    elif source == "azure-kv":
        provider = AzureKvProvider(
            vault_url=f"https://{config.get('vault', '')}.vault.azure.net",
            key_name=config.get("key", ""),
        )
    else:
        raise ValueError(f"Unknown source: {source}")

    record = provider.resolve(ref)
    return record.material
