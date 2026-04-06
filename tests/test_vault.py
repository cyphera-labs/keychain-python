"""Tests for VaultProvider."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cyphera_keychain.vault import VaultProvider
from cyphera_keychain.provider import KeyDisabledError, KeyNotFoundError, NoActiveKeyError, Status

MATERIAL_HEX = "aa" * 32  # 32 bytes = 64 hex chars
MATERIAL_BYTES = bytes.fromhex(MATERIAL_HEX)


def _make_secret(data: dict) -> dict:
    return {"data": {"data": data}}


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def provider(mock_client):
    return VaultProvider(client=mock_client)


def _setup_read(client, data: dict):
    client.secrets.kv.v2.read_secret_version.return_value = _make_secret(data)


class TestResolve:
    def test_returns_active_record(self, provider, mock_client):
        _setup_read(mock_client, {
            "version": "1",
            "status": "active",
            "algorithm": "adf1",
            "material": MATERIAL_HEX,
        })
        rec = provider.resolve("customer-primary")
        assert rec.ref == "customer-primary"
        assert rec.version == 1
        assert rec.status == Status.ACTIVE
        assert rec.material == MATERIAL_BYTES

    def test_deprecated_not_returned_as_active(self, provider, mock_client):
        _setup_read(mock_client, {
            "version": "1",
            "status": "deprecated",
            "algorithm": "adf1",
            "material": MATERIAL_HEX,
        })
        with pytest.raises(NoActiveKeyError):
            provider.resolve("customer-primary")

    def test_highest_active_version_returned(self, provider, mock_client):
        import json
        _setup_read(mock_client, {
            "versions": json.dumps([
                {"version": 2, "status": "active", "algorithm": "adf1", "material": MATERIAL_HEX},
                {"version": 1, "status": "deprecated", "algorithm": "adf1", "material": MATERIAL_HEX},
            ])
        })
        rec = provider.resolve("customer-primary")
        assert rec.version == 2

    def test_no_active_raises(self, provider, mock_client):
        _setup_read(mock_client, {
            "version": "1",
            "status": "disabled",
            "algorithm": "adf1",
            "material": MATERIAL_HEX,
        })
        with pytest.raises(NoActiveKeyError):
            provider.resolve("customer-primary")

    def test_missing_path_raises_key_not_found(self, provider, mock_client):
        from hvac.exceptions import InvalidPath
        mock_client.secrets.kv.v2.read_secret_version.side_effect = InvalidPath()
        with pytest.raises(KeyNotFoundError):
            provider.resolve("missing-ref")


class TestResolveVersion:
    def test_specific_version_returned(self, provider, mock_client):
        import json
        _setup_read(mock_client, {
            "versions": json.dumps([
                {"version": 2, "status": "active", "algorithm": "adf1", "material": MATERIAL_HEX},
                {"version": 1, "status": "deprecated", "algorithm": "adf1", "material": MATERIAL_HEX},
            ])
        })
        rec = provider.resolve_version("customer-primary", 1)
        assert rec.version == 1
        assert rec.status == Status.DEPRECATED

    def test_disabled_raises(self, provider, mock_client):
        _setup_read(mock_client, {
            "version": "1",
            "status": "disabled",
            "algorithm": "adf1",
            "material": MATERIAL_HEX,
        })
        with pytest.raises(KeyDisabledError):
            provider.resolve_version("customer-primary", 1)

    def test_missing_version_raises(self, provider, mock_client):
        _setup_read(mock_client, {
            "version": "1",
            "status": "active",
            "algorithm": "adf1",
            "material": MATERIAL_HEX,
        })
        with pytest.raises(KeyNotFoundError):
            provider.resolve_version("customer-primary", 99)
