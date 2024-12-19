from enum import Enum
from typing import Optional, Union, Callable

import requests
from msal import (
    ConfidentialClientApplication,
    ManagedIdentityClient,
    UserAssignedManagedIdentity,
    SystemAssignedManagedIdentity
)
from redis.auth.err import RequestTokenErr
from redis.auth.idp import IdentityProviderInterface
from redis.auth.token import TokenInterface, JWToken


class ManagedIdentityType(Enum):
    USER_ASSIGNED = UserAssignedManagedIdentity
    SYSTEM_ASSIGNED = SystemAssignedManagedIdentity


class EntraIDIdentityProvider(IdentityProviderInterface):
    """
    EntraID Identity Provider implementation.
    It's recommended to use an additional factory methods to simplify object instantiation.

    Methods: create_provider_from_managed_identity, create_provider_from_service_principal.
    """
    def __init__(
            self,
            app: Union[ManagedIdentityClient, ConfidentialClientApplication],
            scopes : list = [],
            resource: str = '',
            **kwargs
    ):
        self._app = app
        self._scopes = scopes
        self._resource = resource
        self._kwargs = kwargs

    def request_token(self, force_refresh=False) -> TokenInterface:
        """
        Request token from identity provider.
        Force refresh argument is optional and works only with Service Principal auth method.

        :param force_refresh:
        :return: TokenInterface
        """
        if isinstance(self._app, ManagedIdentityClient):
            return self._get_token(self._app.acquire_token_for_client, resource=self._resource)

        if force_refresh:
            self._app.remove_tokens_for_client()

        return self._get_token(
                self._app.acquire_token_for_client,
                scopes=self._scopes,
                **self._kwargs
        )

    def _get_token(self, callback: Callable, **kwargs) -> JWToken:
        try:
            response = callback(**kwargs)

            if "error" in response:
                raise RequestTokenErr(response["error_description"])

            return JWToken(callback(**kwargs)["access_token"])
        except Exception as e:
            raise RequestTokenErr(e)


def create_provider_from_managed_identity(
        identity_type: ManagedIdentityType,
        resource: str,
        client_id: Optional[str] = None,
        object_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
) -> EntraIDIdentityProvider:
    """
    Create an EntraID identity provider following Managed Identity auth flow.

    :param resource_id: Resource ID
    :param object_id: Object ID
    :param client_id: Client ID
    :param identity_type: User Assigned or System Assigned.
    :param resource: Resource for which token should be acquired.
    :param kwargs: Additional arguments you may need during specify to request token.
    See: :class:`ManagedIdentityClient` acquire_token_for_client method.

    :return: :class:`EntraIDIdentityProvider`
    """
    if identity_type == ManagedIdentityType.USER_ASSIGNED:
        kwargs = {
            'client_id': client_id,
            'object_id': object_id,
            'resource_id': resource_id,
        }
        managed_identity = identity_type.value(**kwargs)
    else:
        managed_identity = identity_type.value()

    app = ManagedIdentityClient(managed_identity, http_client=requests.Session())
    return EntraIDIdentityProvider(app, [], resource, **kwargs)


def create_provider_from_service_principal(
        client_credential,
        client_id: str,
        scopes: list = [],
        timeout: Optional[float] = None,
        token_kwargs: dict = {},
        **app_kwargs
) -> EntraIDIdentityProvider:
    """
    Create an EntraID identity provider following Service Principal auth flow.

    :param client_credential: Can be secret string, PEM certificate and more.
    See: :class:`ConfidentialClientApplication`.

    :param client_id: Application (Client) ID.
    :param scopes: If no scopes will be provided, default will be used.
    :param timeout: Timeout in seconds.
    :param token_kwargs: Additional arguments you may need during token request.
    :param app_kwargs: Additional arguments you may need to configure an application.
    :return: :class:`EntraIDIdentityProvider`
    """

    if len(scopes) == 0:
        scopes.append("https://redis.azure.com/.default")

    app = ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_credential,
        timeout=timeout,
        **app_kwargs
    )
    return EntraIDIdentityProvider(app, scopes, **token_kwargs)
