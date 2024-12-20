## Installation
```bash
pip install redis-entraid
```

## Usage

First you have to configure IdentityProvider, for this purpose there's 2 factory methods:
```python
def create_provider_from_managed_identity(
        identity_type: ManagedIdentityType,
        resource: str,
        id_type: Optional[ManagedIdentityIdType] = None,
        id_value: Optional[str] = '',
        **kwargs
) -> EntraIDIdentityProvider

def create_provider_from_service_principal(
        client_credential,
        client_id: str,
        scopes: list = [],
        timeout: Optional[float] = None,
        token_kwargs: dict = {},
        **app_kwargs
) -> EntraIDIdentityProvider
```

This credential provider is running a scheduled background tasks to renew tokens, the specifics
might be configured as well:
```python
auth_config = TokenAuthConfig(idp)
cred_provider = EntraIdCredentialsProvider(auth_config)
```

To obtain token and run background task simply call:
```python
# Sync
cred_provider.get_credentials()

# Async
await cred_provider.get_credentials_async()
```