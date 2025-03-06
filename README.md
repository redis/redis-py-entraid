The `redis-entra-id` Python package helps simplifying the authentication with [Azure Managed Redis](https://azure.microsoft.com/en-us/products/managed-redis) and Azure Cache for Redis using Microsoft Entra ID (formerly Azure Active Directory). It enables seamless integration with Azure's Redis services by fetching authentication tokens and managing the token renewal in the background. This package builds on top of `redis-py` and provides a structured way to authenticate by using a:

* System-assigned managed identity
* User-assigned managed identity
* Service principal

You can learn more about managed identities in the [Microsoft Entra ID documentation](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview).

## Preparation 

### Create a service principal in Azure

In this quick start guide, you will [register an application and create a service principal](https://learn.microsoft.com/en-us/entra/identity-platform/app-objects-and-service-principals?tabs=browser) in Azure. Then the following credentials are used to authenticate via Entra ID:

* Tenant id
* Client id
* Client secret

### Create cache and grant access

Create a Redis cache in Azure and grant your service principal access:

1. Create a cache resource and wait until it was created successfully
2. Navigate to `Settings/Authentication`
3. If needed, enable Entra ID authentication
4. Assign your previously created service principal to the cache

Further details are available in the [AMR](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/managed-redis/managed-redis-entra-for-authentication) or [ACR](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-azure-active-directory-for-authentication) documentation.

### Install the Entra ID package

You need to install the `redis-py` Entra ID package via the following command:

```bash
pip install redis-entra-id
```

The package depends on [redis-py](https://github.com/redis/redis-py).

## Usage

### Step 1 - Import the dependencies

After having installed the package, you can import its modules:

```python
from redis import Redis
from redis_entraid.cred_provider import *
```

### Step 2 - Create the credential provider via the factory method

Following factory methods are offered depends on authentication type you need:

`create_from_managed_identity` - Creates a credential provider based on a managed identity. 
Managed identities allow Azure services to authenticate without needing explicit credentials, as they are automatically assigned by Azure.

`create_from_service_principal` - Creates a credential provider using a service principal. 
A service principal is typically used when you want to authenticate as an application, rather than as a user, with Azure Active Directory.

`create_from_default_azure_credential` - Creates a credential provider from a Default Azure Credential. 
This method allows automatic selection of the appropriate credential mechanism based on the environment 
(e.g., environment variables, managed identities, service principal, interactive browser etc.).

#### Examples ####

**Managed Identity**

```python
credential_provider = create_from_managed_identity(
    identity_type=ManagedIdentityType.SYSTEM_ASSIGNED,
    resource="https://redis.azure.com/"
)
```

**Service principal**

```python
credential_provider = create_from_service_principal(
    CLIENT_ID, 
    CLIENT_SECRET, 
    TENANT_ID
)
```

**Default Azure Credential**

```python
credential_provider = create_from_default_azure_credential(
    ("https://redis.azure.com/.default",),
)
```

More examples available in [examples](https://github.com/redis/redis-py-entraid/tree/vv-default-azure-credentials/examples)
folder.

### Step 3 - Provide optional token renewal configuration

The default configuration would be applied, but you're able to customise it.
  
```python
credential_provider = create_from_service_principal(
    CLIENT_ID, 
    CLIENT_SECRET, 
    TENANT_ID,
    token_manager_config=TokenManagerConfig(
        expiration_refresh_ratio=0.9,
        lower_refresh_bound_millis=DEFAULT_LOWER_REFRESH_BOUND_MILLIS,
        token_request_execution_timeout_in_ms=DEFAULT_TOKEN_REQUEST_EXECUTION_TIMEOUT_IN_MS,
        retry_policy=RetryPolicy(
            max_attempts=5,
            delay_in_ms=50
        )
    )
)
```

You can test the credentials provider by obtaining a token. The following example demonstrates both, a synchronous and an asynchronous approach:

```python
# Synchronous
credential_provider.get_credentials()

# Asynchronous
await credential_provider.get_credentials_async()
```

### Step 4 - Connect to Redis

When using Entra ID, Azure enforces TLS on your Redis connection. Here is an example that shows how to **test** the connection in an insecure way:

```python
client = Redis(host=HOST, port=PORT, ssl=True, ssl_cert_reqs=None, credential_provider=credential_provider)
print("The database size is: {}".format(client.dbsize()))
```
