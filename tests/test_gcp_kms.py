"""Tests for GcpKmsProvider."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cyphera_keychain.gcp_kms import GcpKmsProvider
from cyphera_keychain.provider import KeyNotFoundError, Status

KEY_NAME = "projects/test-project/locations/global/keyRings/test-ring/cryptoKeys/test-key"


@pytest.fixture
def mock_kms_client():
    client = MagicMock()
    resp = MagicMock()
    resp.ciphertext = b"\xcc" * 64
    client.encrypt.return_value = resp
    return client


@pytest.fixture
def provider(mock_kms_client):
    return GcpKmsProvider(KEY_NAME, client=mock_kms_client)


class TestResolve:
    def test_returns_active_record(self, provider):
        rec = provider.resolve("customer-primary")
        assert rec.ref == "customer-primary"
        assert rec.version == 1
        assert rec.status == Status.ACTIVE
        assert len(rec.material) == 32

    def test_calls_encrypt(self, provider, mock_kms_client):
        provider.resolve("customer-primary")
        mock_kms_client.encrypt.assert_called_once()
        req = mock_kms_client.encrypt.call_args[1]["request"]
        assert req["name"] == KEY_NAME
        assert req["additional_authenticated_data"] == b"customer-primary"

    def test_caches_result(self, provider, mock_kms_client):
        r1 = provider.resolve("customer-primary")
        r2 = provider.resolve("customer-primary")
        assert r1.material == r2.material
        assert mock_kms_client.encrypt.call_count == 1

    def test_different_refs_separate_calls(self, provider, mock_kms_client):
        provider.resolve("key-a")
        provider.resolve("key-b")
        assert mock_kms_client.encrypt.call_count == 2


class TestResolveVersion:
    def test_version_one_resolves(self, provider):
        rec = provider.resolve_version("customer-primary", 1)
        assert rec.version == 1

    def test_other_version_raises(self, provider):
        with pytest.raises(KeyNotFoundError):
            provider.resolve_version("customer-primary", 2)


class TestErrorHandling:
    def test_api_error_raises_key_not_found(self):
        from google.api_core.exceptions import GoogleAPICallError

        client = MagicMock()
        client.encrypt.side_effect = GoogleAPICallError("rpc error")
        p = GcpKmsProvider(KEY_NAME, client=client)
        with pytest.raises(KeyNotFoundError):
            p.resolve("bad-ref")
