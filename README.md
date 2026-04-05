# Cyphera Keychain — Python

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

## License

MIT
