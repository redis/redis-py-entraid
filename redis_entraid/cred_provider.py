from typing import Union, Tuple, Callable, Any, Awaitable, Optional, List

from redis.auth.idp import IdentityProviderInterface
from redis.credentials import StreamingCredentialProvider
from redis.auth.token_manager import TokenManagerConfig, RetryPolicy, TokenManager, CredentialsListener

from redis_entraid.identity_provider import ManagedIdentityType, ManagedIdentityIdType, \
    _create_provider_from_managed_identity, ManagedIdentityProviderConfig, ServicePrincipalIdentityProviderConfig, \
    _create_provider_from_service_principal, DefaultAzureCredentialIdentityProviderConfig, \
    _create_provider_from_default_azure_credential

DEFAULT_EXPIRATION_REFRESH_RATIO = 0.7
DEFAULT_LOWER_REFRESH_BOUND_MILLIS = 0
DEFAULT_TOKEN_REQUEST_EXECUTION_TIMEOUT_IN_MS = 100
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_DELAY_IN_MS = 3

class EntraIdCredentialsProvider(StreamingCredentialProvider):
    def __init__(
            self,
            identity_provider: IdentityProviderInterface,
            token_manager_config: TokenManagerConfig,
            initial_delay_in_ms: float = 0,
            block_for_initial: bool = False,
    ):
        """
        :param identity_provider: Identity provider instance
        :param token_manager_config: Token manager specific configuration.
        :param initial_delay_in_ms: Initial delay before run background refresh (valid for async only)
        :param block_for_initial: Block execution until initial token will be acquired (valid for async only)
        """
        self._idp = identity_provider
        self._token_mgr = TokenManager(
            self._idp,
            token_manager_config
        )
        self._listener = CredentialsListener()
        self._is_streaming = False
        self._initial_delay_in_ms = initial_delay_in_ms
        self._block_for_initial = block_for_initial

    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        """
        Acquire token from the identity provider.
        """
        init_token = self._token_mgr.acquire_token()

        if self._is_streaming is False:
            self._token_mgr.start(
                self._listener,
                skip_initial=True
            )
            self._is_streaming = True

        return init_token.get_token().try_get('oid'), init_token.get_token().get_value()

    async def get_credentials_async(self) -> Union[Tuple[str], Tuple[str, str]]:
        """
        Acquire token from the identity provider in async mode.
        """
        init_token = await self._token_mgr.acquire_token_async()

        if self._is_streaming is False:
            await self._token_mgr.start_async(
                self._listener,
                initial_delay_in_ms=self._initial_delay_in_ms,
                block_for_initial=self._block_for_initial,
                skip_initial=True
            )
            self._is_streaming = True

        return init_token.get_token().try_get('oid'), init_token.get_token().get_value()

    def on_next(self, callback: Union[Callable[[Any], None], Awaitable]):
        self._listener.on_next = callback

    def on_error(self, callback: Union[Callable[[Exception], None], Awaitable]):
        self._listener.on_error = callback

    def is_streaming(self) -> bool:
        return self._is_streaming


def create_from_managed_identity(
        identity_type: ManagedIdentityType,
        resource: str,
        id_type: Optional[ManagedIdentityIdType] = None,
        id_value: Optional[str] = '',
        kwargs: Optional[dict] = {},
        token_manager_config: Optional[TokenManagerConfig] = TokenManagerConfig(
            DEFAULT_EXPIRATION_REFRESH_RATIO,
            DEFAULT_LOWER_REFRESH_BOUND_MILLIS,
            DEFAULT_TOKEN_REQUEST_EXECUTION_TIMEOUT_IN_MS,
            RetryPolicy(
                DEFAULT_MAX_ATTEMPTS,
                DEFAULT_DELAY_IN_MS
            )
        )
) -> EntraIdCredentialsProvider:
    """
    Create a credential provider from a managed identity type.

    :param identity_type: Managed identity type.
    :param resource: Identity provider resource.
    :param id_type: Identity provider type.
    :param id_value: Identity provider value.
    :param kwargs: Optional keyword arguments to pass to identity provider. See: :class:`ManagedIdentityClient`
    :param token_manager_config: Token manager specific configuration.
    :return: EntraIdCredentialsProvider instance.
    """
    managed_identity_config = ManagedIdentityProviderConfig(
        identity_type=identity_type,
        resource=resource,
        id_type=id_type,
        id_value=id_value,
        kwargs=kwargs
    )
    idp = _create_provider_from_managed_identity(managed_identity_config)
    return EntraIdCredentialsProvider(idp, token_manager_config)


def create_from_service_principal(
        client_id: str,
        client_credential: Any,
        tenant_id: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        token_kwargs: Optional[dict] = {},
        app_kwargs: Optional[dict] = {},
        token_manager_config: Optional[TokenManagerConfig] = TokenManagerConfig(
            DEFAULT_EXPIRATION_REFRESH_RATIO,
            DEFAULT_LOWER_REFRESH_BOUND_MILLIS,
            DEFAULT_TOKEN_REQUEST_EXECUTION_TIMEOUT_IN_MS,
            RetryPolicy(
                DEFAULT_MAX_ATTEMPTS,
                DEFAULT_DELAY_IN_MS
                )
            )) -> EntraIdCredentialsProvider:
    """
    Create a credential provider from a service principal.

    :param client_credential: Service principal credentials.
    :param client_id: Service principal client ID.
    :param scopes: Service principal scopes. Fallback to default scopes if None.
    :param timeout: Service principal timeout.
    :param tenant_id: Service principal tenant ID.
    :param token_kwargs: Optional token arguments to pass to service identity provider.
    :param app_kwargs: Optional keyword arguments to pass to service principal application.
    :param token_manager_config: Token manager specific configuration.
    :return: EntraIdCredentialsProvider instance.
    """
    service_principal_config = ServicePrincipalIdentityProviderConfig(
        client_credential=client_credential,
        client_id=client_id,
        scopes=scopes,
        timeout=timeout,
        tenant_id=tenant_id,
        app_kwargs=app_kwargs,
        token_kwargs=token_kwargs,
    )
    idp = _create_provider_from_service_principal(service_principal_config)
    return EntraIdCredentialsProvider(idp, token_manager_config)


def create_from_default_azure_credential(
        scopes: Tuple[str],
        tenant_id: Optional[str] = None,
        authority: Optional[str] = None,
        token_kwargs: Optional[dict] = {},
        app_kwargs: Optional[dict] = {},
        token_manager_config: Optional[TokenManagerConfig] = TokenManagerConfig(
            DEFAULT_EXPIRATION_REFRESH_RATIO,
            DEFAULT_LOWER_REFRESH_BOUND_MILLIS,
            DEFAULT_TOKEN_REQUEST_EXECUTION_TIMEOUT_IN_MS,
            RetryPolicy(
                DEFAULT_MAX_ATTEMPTS,
                DEFAULT_DELAY_IN_MS
            )
        )
) -> EntraIdCredentialsProvider:
    """
    Create a credential provider from a Default Azure credential.
    https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential?view=azure-python

    :param scopes: Service principal scopes. Fallback to default scopes if None.
    :param tenant_id: Optional tenant to include in the token request.
    :param authority: Custom authority, by default used  'login.microsoftonline.com'
    :param token_kwargs: Optional token arguments applied when retrieving tokens.
    :param app_kwargs: Optional keyword arguments to pass when instantiating application.
    :param token_manager_config: Token manager specific configuration.
    """
    default_azure_credential_config = DefaultAzureCredentialIdentityProviderConfig(
        scopes=scopes,
        authority=authority,
        additional_tenant_id=tenant_id,
        token_kwargs=token_kwargs,
        app_kwargs=app_kwargs,
    )
    idp = _create_provider_from_default_azure_credential(default_azure_credential_config)
    return EntraIdCredentialsProvider(idp, token_manager_config)