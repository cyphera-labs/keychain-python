from __future__ import annotations

import pytest

from cyphera_keychain import (
    FileProvider,
    KeyDisabledError,
    KeyNotFoundError,
    Status,
)

KEY_HEX = "0123456789abcdef0123456789abcdef"
KEY_BYTES = bytes.fromhex(KEY_HEX)
TWEAK_HEX = "deadbeef"
TWEAK_BYTES = bytes.fromhex(TWEAK_HEX)

_ACTIVE_KEY = {
    "ref": "customer-primary",
    "version": 1,
    "status": "active",
    "algorithm": "adf1",
    "material": KEY_HEX,
}

_DISABLED_KEY = {
    "ref": "customer-primary",
    "version": 2,
    "status": "disabled",
    "algorithm": "adf1",
    "material": KEY_HEX,
}


class TestLoadFromFile:
    def test_load_active_key(self, tmp_key_file):
        path = tmp_key_file([_ACTIVE_KEY])
        provider = FileProvider(path)
        record = provider.resolve("customer-primary")
        assert record.ref == "customer-primary"
        assert record.version == 1
        assert record.status == Status.ACTIVE
        assert record.material == KEY_BYTES
        assert record.algorithm == "adf1"

    def test_load_tweak(self, tmp_key_file):
        key = {**_ACTIVE_KEY, "tweak": TWEAK_HEX}
        path = tmp_key_file([key])
        provider = FileProvider(path)
        record = provider.resolve("customer-primary")
        assert record.tweak == TWEAK_BYTES

    def test_no_tweak_is_none(self, tmp_key_file):
        path = tmp_key_file([_ACTIVE_KEY])
        provider = FileProvider(path)
        record = provider.resolve("customer-primary")
        assert record.tweak is None

    def test_load_created_at(self, tmp_key_file):
        from datetime import datetime

        key = {**_ACTIVE_KEY, "created_at": "2024-01-15T10:30:00"}
        path = tmp_key_file([key])
        provider = FileProvider(path)
        record = provider.resolve("customer-primary")
        assert record.created_at == datetime(2024, 1, 15, 10, 30, 0)

    def test_load_metadata(self, tmp_key_file):
        key = {**_ACTIVE_KEY, "metadata": {"env": "prod", "team": "core"}}
        path = tmp_key_file([key])
        provider = FileProvider(path)
        record = provider.resolve("customer-primary")
        assert record.metadata == {"env": "prod", "team": "core"}


class TestResolve:
    def test_resolve_active_key(self, tmp_key_file):
        path = tmp_key_file([_ACTIVE_KEY])
        provider = FileProvider(path)
        record = provider.resolve("customer-primary")
        assert record.version == 1

    def test_resolve_returns_highest_active_version(self, tmp_key_file):
        v1 = {**_ACTIVE_KEY, "version": 1, "status": "deprecated"}
        v2 = {**_ACTIVE_KEY, "version": 2, "status": "active"}
        path = tmp_key_file([v1, v2])
        provider = FileProvider(path)
        record = provider.resolve("customer-primary")
        assert record.version == 2

    def test_resolve_missing_ref_raises(self, tmp_key_file):
        path = tmp_key_file([_ACTIVE_KEY])
        provider = FileProvider(path)
        with pytest.raises(KeyNotFoundError) as exc_info:
            provider.resolve("nonexistent")
        assert exc_info.value.ref == "nonexistent"

    def test_resolve_disabled_key_raises_no_active(self, tmp_key_file):
        from cyphera_keychain import NoActiveKeyError

        path = tmp_key_file([_DISABLED_KEY])
        provider = FileProvider(path)
        with pytest.raises(NoActiveKeyError):
            provider.resolve("customer-primary")


class TestResolveVersion:
    def test_resolve_version_correct_record(self, tmp_key_file):
        v1 = {**_ACTIVE_KEY, "version": 1, "status": "active"}
        v2 = {**_ACTIVE_KEY, "version": 2, "status": "active"}
        path = tmp_key_file([v1, v2])
        provider = FileProvider(path)
        record = provider.resolve_version("customer-primary", 1)
        assert record.version == 1

    def test_resolve_version_missing_ref_raises(self, tmp_key_file):
        path = tmp_key_file([_ACTIVE_KEY])
        provider = FileProvider(path)
        with pytest.raises(KeyNotFoundError) as exc_info:
            provider.resolve_version("nonexistent", 1)
        assert exc_info.value.ref == "nonexistent"

    def test_resolve_version_disabled_raises(self, tmp_key_file):
        path = tmp_key_file([_DISABLED_KEY])
        provider = FileProvider(path)
        with pytest.raises(KeyDisabledError) as exc_info:
            provider.resolve_version("customer-primary", 2)
        assert exc_info.value.ref == "customer-primary"
        assert exc_info.value.version == 2

    def test_resolve_version_missing_version_raises(self, tmp_key_file):
        path = tmp_key_file([_ACTIVE_KEY])
        provider = FileProvider(path)
        with pytest.raises(KeyNotFoundError) as exc_info:
            provider.resolve_version("customer-primary", 99)
        assert exc_info.value.version == 99
