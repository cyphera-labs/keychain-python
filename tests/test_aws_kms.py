"""Tests for AwsKmsProvider."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cyphera_keychain.aws_kms import AwsKmsProvider
from cyphera_keychain.provider import KeyNotFoundError, Status

KEY_ID = "arn:aws:kms:us-east-1:123456789012:key/test-key-id"
FAKE_PLAINTEXT = b"\xaa" * 32
FAKE_CIPHERTEXT = b"\xbb" * 64


@pytest.fixture
def mock_boto_client():
    client = MagicMock()
    client.generate_data_key.return_value = {
        "Plaintext": FAKE_PLAINTEXT,
        "CiphertextBlob": FAKE_CIPHERTEXT,
        "KeyId": KEY_ID,
    }
    return client


@pytest.fixture
def provider(mock_boto_client):
    with patch("boto3.client", return_value=mock_boto_client):
        return AwsKmsProvider(KEY_ID, region="us-east-1")


class TestResolve:
    def test_returns_active_record(self, provider):
        rec = provider.resolve("customer-primary")
        assert rec.ref == "customer-primary"
        assert rec.version == 1
        assert rec.status == Status.ACTIVE
        assert rec.material == FAKE_PLAINTEXT

    def test_algorithm_is_aes256(self, provider):
        rec = provider.resolve("customer-primary")
        assert rec.algorithm == "aes256"

    def test_calls_generate_data_key(self, provider, mock_boto_client):
        provider.resolve("customer-primary")
        mock_boto_client.generate_data_key.assert_called_once_with(
            KeyId=KEY_ID,
            KeySpec="AES_256",
            EncryptionContext={"cyphera:ref": "customer-primary"},
        )

    def test_caches_result(self, provider, mock_boto_client):
        provider.resolve("customer-primary")
        provider.resolve("customer-primary")
        assert mock_boto_client.generate_data_key.call_count == 1

    def test_different_refs_separate_calls(self, provider, mock_boto_client):
        provider.resolve("key-a")
        provider.resolve("key-b")
        assert mock_boto_client.generate_data_key.call_count == 2


class TestResolveVersion:
    def test_version_one_resolves(self, provider):
        rec = provider.resolve_version("customer-primary", 1)
        assert rec.version == 1

    def test_other_versions_raise(self, provider):
        with pytest.raises(KeyNotFoundError):
            provider.resolve_version("customer-primary", 2)


class TestErrorHandling:
    def test_client_error_raises_key_not_found(self):
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.generate_data_key.side_effect = ClientError(
            {"Error": {"Code": "NotFoundException", "Message": "not found"}},
            "GenerateDataKey",
        )
        with patch("boto3.client", return_value=client):
            p = AwsKmsProvider(KEY_ID)
        with pytest.raises(KeyNotFoundError):
            p.resolve("missing-ref")
