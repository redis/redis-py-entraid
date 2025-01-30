## Preparation 

### Create a service principal in Azure

You can [register an application and create a service principal](https://learn.microsoft.com/en-us/entra/identity-platform/app-objects-and-service-principals?tabs=browser) in Azure. Then the following credentials are used to authenticate via Entra ID:

* Tenant id
* Client id
* Client secret

### Create cache and grant access

Create an Azure Cache for Redis instance and grant your service principal access:

1. Create the cache and wait until it was created successfully
2. Navigate to `Settings/Authentication`
3. Enable Entra ID authentication
4. Assign your service principal with the role `Data Owner` to the cache

You can find further details in the [Azure Cache for Redis documentation](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-azure-active-directory-for-authentication).

### Install the Entra ID package

You need to install the `redis-py` Entra ID package via the following command:

```bash
pip install redis-entra-id
```

The package depends on [redis-py](https://github.com/redis/redis-py/tree/v5.3.0b4) version `5.3.0b4`.

## Usage

### Step 1 - Import the dependencies

After having installed the package, you can import its modules:

```python
import redis
from redis_entraid import identity_provider
from redis_entraid import cred_provider
```

### Step 2 - Define your authority based on the tenant ID

```python
authority = "{}/{}".format("https://login.microsoftonline.com", "<TENANT_ID>")
```

> This step is going to be removed in the next pre-release version of `redis-py-entraid`. Instead, the factory method will allow to pass the tenant id direclty.

### Step 3 - Create the identity provider via the factory method

```python
idp = identity_provider.create_provider_from_service_principal("<CLIENT_SECRET>", "<CLIENT_ID>", authority=authority)
```

### Step 4 - Initialize a credentials provider from the authentication configuration

You can use the default configuration or customize the background task for token renewal.
  
```python
auth_config = TokenAuthConfig(idp)
cred_provider = EntraIdCredentialsProvider(auth_config)
```

You can test the credentials provider by obtaining a token. The following example demonstrates both, a synchronous and an asynchronous approach:

```python
# Synchronous
cred_provider.get_credentials()

# Asynchronous
await cred_provider.get_credentials_async()
```

### Step 5 - Connect to Redis

When using Entra ID, Azure Cache for Redis enforces TLS. Here is an example that shows how to test the connection in an insecure way:

```python
client = redis.Redis(host="<HOST>", port=<PORT>, ssl=True, ssl_cert_reqs=None, credential_provider=cred_provider)
print("The database size is: {}".format(client.dbsize()))
```
