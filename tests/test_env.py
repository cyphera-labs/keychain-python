from __future__ import annotations

import base64

import pytest

from cyphera_keychain import EnvProvider, KeyNotFoundError, Status


KEY_HEX = "0123456789abcdef0123456789abcdef"
KEY_BYTES = bytes.fromhex(KEY_HEX)
KEY_B64 = base64.b64encode(KEY_BYTES).decode()
TWEAK_HEX = "deadbeef"
TWEAK_BYTES = bytes.fromhex(TWEAK_HEX)


class TestResolveHex:
    def test_resolve_hex_key(self, monkeypatch):
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_KEY", KEY_HEX)
        provider = EnvProvider(prefix="CYPHERA")
        record = provider.resolve("customer-primary")
        assert record.material == KEY_BYTES
        assert record.ref == "customer-primary"
        assert record.version == 1
        assert record.status == Status.ACTIVE
        assert record.tweak is None

    def test_resolve_hex_key_no_prefix_underscore(self, monkeypatch):
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_KEY", KEY_HEX)
        # Prefix with trailing underscore should still work
        provider = EnvProvider(prefix="CYPHERA_")
        record = provider.resolve("customer-primary")
        assert record.material == KEY_BYTES


class TestResolveBase64:
    def test_resolve_base64_key(self, monkeypatch):
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_KEY", KEY_B64)
        provider = EnvProvider(prefix="CYPHERA")
        record = provider.resolve("customer-primary")
        assert record.material == KEY_BYTES

    def test_resolve_urlsafe_base64_key(self, monkeypatch):
        url_safe = base64.urlsafe_b64encode(KEY_BYTES).decode()
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_KEY", url_safe)
        provider = EnvProvider(prefix="CYPHERA")
        record = provider.resolve("customer-primary")
        assert record.material == KEY_BYTES


class TestMissingKey:
    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("CYPHERA_CUSTOMER_PRIMARY_KEY", raising=False)
        provider = EnvProvider(prefix="CYPHERA")
        with pytest.raises(KeyNotFoundError) as exc_info:
            provider.resolve("customer-primary")
        assert exc_info.value.ref == "customer-primary"


class TestResolveVersion:
    def test_resolve_version_1_works(self, monkeypatch):
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_KEY", KEY_HEX)
        provider = EnvProvider(prefix="CYPHERA")
        record = provider.resolve_version("customer-primary", 1)
        assert record.version == 1
        assert record.material == KEY_BYTES

    def test_resolve_version_2_raises(self, monkeypatch):
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_KEY", KEY_HEX)
        provider = EnvProvider(prefix="CYPHERA")
        with pytest.raises(KeyNotFoundError) as exc_info:
            provider.resolve_version("customer-primary", 2)
        assert exc_info.value.ref == "customer-primary"
        assert exc_info.value.version == 2


class TestTweak:
    def test_tweak_read_when_set(self, monkeypatch):
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_KEY", KEY_HEX)
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_TWEAK", TWEAK_HEX)
        provider = EnvProvider(prefix="CYPHERA")
        record = provider.resolve("customer-primary")
        assert record.tweak == TWEAK_BYTES

    def test_tweak_none_when_not_set(self, monkeypatch):
        monkeypatch.setenv("CYPHERA_CUSTOMER_PRIMARY_KEY", KEY_HEX)
        monkeypatch.delenv("CYPHERA_CUSTOMER_PRIMARY_TWEAK", raising=False)
        provider = EnvProvider(prefix="CYPHERA")
        record = provider.resolve("customer-primary")
        assert record.tweak is None

    def test_ref_with_dots_normalized(self, monkeypatch):
        monkeypatch.setenv("CYPHERA_CUSTOMER_V2_KEY", KEY_HEX)
        provider = EnvProvider(prefix="CYPHERA")
        record = provider.resolve("customer.v2")
        assert record.material == KEY_BYTES
