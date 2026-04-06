"""Integration tests for AwsKmsProvider against LocalStack."""
from __future__ import annotations

import os

import boto3
import pytest

from cyphera_keychain.aws_kms import AwsKmsProvider
from cyphera_keychain.provider import Status

LOCALSTACK_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
AWS_KEY_ID = os.environ.get("AWS_KMS_KEY_ID", "")


@pytest.fixture(scope="module")
def kms_key_id():
    client = boto3.client(
        "kms",
        region_name=AWS_REGION,
        endpoint_url=LOCALSTACK_URL,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
    )
    if AWS_KEY_ID:
        return AWS_KEY_ID
    resp = client.create_key(Description="Cyphera integration test key")
    return resp["KeyMetadata"]["KeyId"]


@pytest.fixture(scope="module")
def provider(kms_key_id):
    return AwsKmsProvider(
        kms_key_id,
        region=AWS_REGION,
        endpoint_url=LOCALSTACK_URL,
    )


@pytest.mark.integration
class TestAwsKmsIntegration:
    def test_resolve_returns_active_record(self, provider):
        rec = provider.resolve("customer-primary")
        assert rec.ref == "customer-primary"
        assert rec.status == Status.ACTIVE
        assert len(rec.material) == 32

    def test_resolve_caches_key(self, provider):
        r1 = provider.resolve("cached-ref")
        r2 = provider.resolve("cached-ref")
        assert r1.material == r2.material

    def test_resolve_version_1(self, provider):
        rec = provider.resolve_version("versioned-ref", 1)
        assert rec.version == 1
