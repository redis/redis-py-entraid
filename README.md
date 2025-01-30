## Installation
```bash
pip install redis-entraid
```

## Usage

### Step 1 - Import the dependencies

The `redis-py-entraid` package has a dependency on `redis-py` version `5.3.0b4`.

```python
import redis
from redis_entraid import identity_provider
from redis_entraid import cred_provider
```

### Step 2 - Define your authority based on the tenant id

```python
authority = "{}/{}".format("https://login.microsoftonline.com", "<TENANT_ID>")
```

### Step 3 - Create the identity provider via the factory method

```python
idp = identity_provider.create_provider_from_service_principal("<CLIENT_SECRET>", "<CLIENT_ID>", authority=authority)
```

### Step 4 - Initialize a credentials provider from the authentication configuration

You can use the default configuration or configure the background task in regards to token renewal.
  
```python
auth_config = TokenAuthConfig(idp)
cred_provider = EntraIdCredentialsProvider(auth_config)
```

You can test the credentials provider by trying to obtain a token. The following example shows how to do this synchronously and asynchronously.

```python
# Sync
cred_provider.get_credentials()

# Async
await cred_provider.get_credentials_async()
```

### Step 5 - Connect to Redis

Azure Cache for Redis enforces TLS. The following example shows how you can test the connection in an insecure way:

```python
client = redis.Redis(host="<HOST>", port=<PORT>, ssl=True, ssl_cert_reqs=None, credential_provider=cred_provider)
print("The database size is: {}".format(client.dbsize()))
```
