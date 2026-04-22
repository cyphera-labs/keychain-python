# Cyphera Keychain — Python

[![CI](https://github.com/cyphera-labs/keychain-python/actions/workflows/ci.yml/badge.svg)](https://github.com/cyphera-labs/keychain-python/actions/workflows/ci.yml)
[![Security](https://github.com/cyphera-labs/keychain-python/actions/workflows/codeql.yml/badge.svg)](https://github.com/cyphera-labs/keychain-python/actions/workflows/codeql.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
Key provider abstraction for the [Cyphera](https://cyphera.dev) Python SDK.

## Installation

```sh
pip install cyphera-keychain
```

## Usage

### Memory provider (testing / development)

```python
from cyphera_keychain import MemoryProvider, KeyRecord, Status

provider = MemoryProvider(
    KeyRecord(
        ref="customer-primary",
        version=1,
        status=Status.ACTIVE,
        material=bytes.fromhex("0123456789abcdef0123456789abcdef"),
        tweak=b"customer-ssn",
    )
)

record = provider.resolve("customer-primary")
```

### Environment variable provider

```python
from cyphera_keychain import EnvProvider

# Reads CYPHERA_CUSTOMER_PRIMARY_KEY (hex or base64)
provider = EnvProvider(prefix="CYPHERA")
record = provider.resolve("customer-primary")
```

### File provider

```python
from cyphera_keychain import FileProvider

provider = FileProvider("/etc/cyphera/keys.json")
record = provider.resolve("customer-primary")
```

Key file format:

```json
{
  "keys": [
    {
      "ref": "customer-primary",
      "version": 1,
      "status": "active",
      "algorithm": "adf1",
      "material": "<hex or base64>",
      "tweak": "<hex or base64>"
    }
  ]
}
```

## Providers

| Provider | Description | Use case |
|---|---|---|
| `MemoryProvider` | In-memory key store | Testing, development |
| `EnvProvider` | Keys from environment variables | 12-factor / container deployments |
| `FileProvider` | Keys from a local JSON file | Secrets manager file injection |
| `AwsKmsProvider` | AWS KMS data-key generation | AWS workloads |
| `GcpKmsProvider` | GCP Cloud KMS envelope encryption | GCP workloads |
| `AzureKvProvider` | Azure Key Vault RSA key-wrapping | Azure workloads |
| `VaultProvider` | HashiCorp Vault KV v2 secrets | Multi-cloud / on-prem |

## Cloud KMS Providers

Cyphera ships four cloud-native providers for production deployments. Each generates or retrieves a 256-bit AES data key via the respective KMS service and caches the plaintext for the lifetime of the provider object.

### AWS KMS

```sh
pip install "cyphera-keychain[aws]"
```

```python
from cyphera_keychain import AwsKmsProvider

provider = AwsKmsProvider(
    "arn:aws:kms:us-east-1:123456789012:key/my-key-id",
    region="us-east-1",
)

record = provider.resolve("customer-primary")
# record.material  ->  32-byte AES-256 data key
```

The provider calls `GenerateDataKey` with `KeySpec=AES_256` and sets
`EncryptionContext={"cyphera:ref": ref}` for auditability. Results are cached
per `ref` so subsequent calls within the same process do not incur additional
KMS API calls.

### GCP Cloud KMS

```sh
pip install "cyphera-keychain[gcp]"
```

```python
from cyphera_keychain import GcpKmsProvider

KEY_NAME = (
    "projects/my-project/locations/global"
    "/keyRings/my-ring/cryptoKeys/my-key"
)

provider = GcpKmsProvider(KEY_NAME)
record = provider.resolve("customer-primary")
```

A random 32-byte plaintext key is generated locally with `os.urandom(32)` and
wrapped via `Encrypt` (with the ref as additional authenticated data). The
plaintext is cached in memory; the ciphertext is discarded after wrapping.

### Azure Key Vault

```sh
pip install "cyphera-keychain[azure]"
```

```python
from cyphera_keychain import AzureKvProvider

provider = AzureKvProvider(
    vault_url="https://my-vault.vault.azure.net",
    key_name="my-rsa-key",
)

record = provider.resolve("customer-primary")
```

A random 32-byte key is wrapped with the named RSA key using RSA-OAEP via the
Azure Key Vault `CryptographyClient`. Authentication defaults to
`DefaultAzureCredential`; pass a custom `credential` to override.

### HashiCorp Vault (KV v2)

```sh
pip install "cyphera-keychain[vault]"
```

```python
from cyphera_keychain import VaultProvider

provider = VaultProvider(
    url="https://vault.internal.example.com",
    token="s.mytoken",
    mount="secret",
)

record = provider.resolve("customer-primary")
```

Key records are read from Vault KV v2 at path `{mount}/{ref}`. The secret data
must contain `version`, `status`, `algorithm`, and `material` fields (hex or
base64). Multi-version keys can be stored as a `versions` JSON array for
rotation support.

## License

Apache 2.0
