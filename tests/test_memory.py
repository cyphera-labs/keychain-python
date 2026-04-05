from __future__ import annotations

import pytest

from cyphera_keychain import (
    KeyDisabledError,
    KeyNotFoundError,
    KeyRecord,
    MemoryProvider,
    NoActiveKeyError,
    Status,
)

KEY_MATERIAL = bytes.fromhex("0123456789abcdef0123456789abcdef")


def make_record(ref: str = "k", version: int = 1, status: Status = Status.ACTIVE) -> KeyRecord:
    return KeyRecord(ref=ref, version=version, status=status, material=KEY_MATERIAL)


class TestResolve:
    def test_resolve_active_key(self):
        provider = MemoryProvider(make_record("k", 1, Status.ACTIVE))
        record = provider.resolve("k")
        assert record.ref == "k"
        assert record.version == 1
        assert record.status == Status.ACTIVE

    def test_resolve_unknown_ref_raises(self):
        provider = MemoryProvider()
        with pytest.raises(KeyNotFoundError) as exc_info:
            provider.resolve("missing")
        assert exc_info.value.ref == "missing"
        assert exc_info.value.version is None

    def test_resolve_no_active_key_raises(self):
        provider = MemoryProvider(
            make_record("k", 1, Status.DEPRECATED),
            make_record("k", 2, Status.DISABLED),
        )
        with pytest.raises(NoActiveKeyError) as exc_info:
            provider.resolve("k")
        assert exc_info.value.ref == "k"

    def test_resolve_returns_highest_active_version(self):
        provider = MemoryProvider(
            make_record("k", 1, Status.ACTIVE),
            make_record("k", 2, Status.ACTIVE),
            make_record("k", 3, Status.DEPRECATED),
        )
        record = provider.resolve("k")
        assert record.version == 2

    def test_resolve_skips_deprecated_returns_next_active(self):
        provider = MemoryProvider(
            make_record("k", 1, Status.ACTIVE),
            make_record("k", 2, Status.DEPRECATED),
        )
        record = provider.resolve("k")
        assert record.version == 1


class TestResolveVersion:
    def test_resolve_version_returns_correct_record(self):
        provider = MemoryProvider(
            make_record("k", 1, Status.ACTIVE),
            make_record("k", 2, Status.ACTIVE),
        )
        record = provider.resolve_version("k", 1)
        assert record.version == 1

    def test_resolve_version_disabled_raises(self):
        provider = MemoryProvider(make_record("k", 1, Status.DISABLED))
        with pytest.raises(KeyDisabledError) as exc_info:
            provider.resolve_version("k", 1)
        assert exc_info.value.ref == "k"
        assert exc_info.value.version == 1

    def test_resolve_version_missing_ref_raises(self):
        provider = MemoryProvider()
        with pytest.raises(KeyNotFoundError) as exc_info:
            provider.resolve_version("missing", 1)
        assert exc_info.value.ref == "missing"
        assert exc_info.value.version == 1

    def test_resolve_version_missing_version_raises(self):
        provider = MemoryProvider(make_record("k", 1, Status.ACTIVE))
        with pytest.raises(KeyNotFoundError) as exc_info:
            provider.resolve_version("k", 99)
        assert exc_info.value.version == 99

    def test_resolve_version_deprecated_allowed(self):
        provider = MemoryProvider(make_record("k", 1, Status.DEPRECATED))
        record = provider.resolve_version("k", 1)
        assert record.version == 1
        assert record.status == Status.DEPRECATED


class TestAdd:
    def test_add_makes_key_resolvable(self):
        provider = MemoryProvider()
        provider.add(make_record("k", 1, Status.ACTIVE))
        record = provider.resolve("k")
        assert record.version == 1

    def test_add_updates_highest_active(self):
        provider = MemoryProvider(make_record("k", 1, Status.ACTIVE))
        provider.add(make_record("k", 2, Status.ACTIVE))
        record = provider.resolve("k")
        assert record.version == 2

    def test_add_multiple_refs(self):
        provider = MemoryProvider()
        provider.add(make_record("alpha", 1, Status.ACTIVE))
        provider.add(make_record("beta", 1, Status.ACTIVE))
        assert provider.resolve("alpha").ref == "alpha"
        assert provider.resolve("beta").ref == "beta"
