"""Tests for AzureKvProvider."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cyphera_keychain.azure_kv import AzureKvProvider
from cyphera_keychain.provider import KeyNotFoundError, Status

VAULT_URL = "https://test-vault.vault.azure.net"
KEY_NAME = "test-rsa-key"


@pytest.fixture
def mock_key_client():
    client = MagicMock()
    client.get_key.return_value = MagicMock()
    return client


@pytest.fixture
def mock_crypto_client():
    client = MagicMock()
    wrap_result = MagicMock()
    wrap_result.encrypted_key = b"\xdd" * 64
    client.wrap_key.return_value = wrap_result
    return client


@pytest.fixture
def provider(mock_key_client, mock_crypto_client):
    cred = MagicMock()
    with patch("cyphera_keychain.azure_kv.KeyClient", return_value=mock_key_client), \
         patch("cyphera_keychain.azure_kv.CryptographyClient", return_value=mock_crypto_client):
        return AzureKvProvider(VAULT_URL, KEY_NAME, credential=cred)


class TestResolve:
    def test_returns_active_record(self, provider):
        rec = provider.resolve("customer-primary")
        assert rec.ref == "customer-primary"
        assert rec.version == 1
        assert rec.status == Status.ACTIVE
        assert len(rec.material) == 32

    def test_calls_wrap_key(self, provider, mock_crypto_client):
        provider.resolve("customer-primary")
        mock_crypto_client.wrap_key.assert_called_once()

    def test_caches_result(self, provider, mock_crypto_client):
        r1 = provider.resolve("customer-primary")
        r2 = provider.resolve("customer-primary")
        assert r1.material == r2.material
        assert mock_crypto_client.wrap_key.call_count == 1

    def test_different_refs_cached_separately(self, provider, mock_crypto_client):
        provider.resolve("key-a")
        provider.resolve("key-b")
        assert mock_crypto_client.wrap_key.call_count == 2


class TestResolveVersion:
    def test_version_one_resolves(self, provider):
        rec = provider.resolve_version("customer-primary", 1)
        assert rec.version == 1

    def test_other_version_raises(self, provider):
        with pytest.raises(KeyNotFoundError):
            provider.resolve_version("customer-primary", 2)


class TestErrorHandling:
    def test_resource_not_found_raises_key_not_found(self):
        from azure.core.exceptions import ResourceNotFoundError as AzureNotFound

        mock_key_client = MagicMock()
        mock_key_client.get_key.side_effect = AzureNotFound("not found")
        cred = MagicMock()
        with patch("cyphera_keychain.azure_kv.KeyClient", return_value=mock_key_client), \
             patch("cyphera_keychain.azure_kv.CryptographyClient", return_value=MagicMock()):
            p = AzureKvProvider(VAULT_URL, KEY_NAME, credential=cred)
        with pytest.raises(KeyNotFoundError):
            p.resolve("missing-key")
