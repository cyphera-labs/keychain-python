"""Integration tests for VaultProvider against HashiCorp Vault dev server."""
from __future__ import annotations

import os

import hvac
import pytest

from cyphera_keychain.vault import VaultProvider
from cyphera_keychain.provider import Status

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "root")
MATERIAL_HEX = "aabbccdd" * 8  # 32 bytes


@pytest.fixture(scope="module")
def vault_client():
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    try:
        client.sys.enable_secrets_engine("kv", path="secret", options={"version": "2"})
    except Exception:
        pass
    return client


@pytest.fixture(scope="module")
def provider():
    return VaultProvider(url=VAULT_ADDR, token=VAULT_TOKEN)


@pytest.mark.integration
class TestVaultIntegration:
    def test_resolve_single_version(self, provider, vault_client):
        vault_client.secrets.kv.v2.create_or_update_secret(
            path="integ-customer-primary",
            secret={
                "version": "1",
                "status": "active",
                "algorithm": "adf1",
                "material": MATERIAL_HEX,
            },
            mount_point="secret",
        )
        rec = provider.resolve("integ-customer-primary")
        assert rec.ref == "integ-customer-primary"
        assert rec.status == Status.ACTIVE
        assert rec.material == bytes.fromhex(MATERIAL_HEX)

    def test_resolve_version_specific(self, provider, vault_client):
        import json
        vault_client.secrets.kv.v2.create_or_update_secret(
            path="integ-versioned-key",
            secret={
                "versions": json.dumps([
                    {"version": 2, "status": "active", "algorithm": "adf1", "material": MATERIAL_HEX},
                    {"version": 1, "status": "deprecated", "algorithm": "adf1", "material": MATERIAL_HEX},
                ])
            },
            mount_point="secret",
        )
        rec = provider.resolve_version("integ-versioned-key", 1)
        assert rec.version == 1
        assert rec.status == Status.DEPRECATED
