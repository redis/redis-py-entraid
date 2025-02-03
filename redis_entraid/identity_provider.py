from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, Callable, Any, List

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


class ManagedIdentityIdType(Enum):
    CLIENT_ID = "client_id"
    OBJECT_ID = "object_id"
    RESOURCE_ID = "resource_id"


@dataclass
class ManagedIdentityProviderConfig:
    identity_type: ManagedIdentityType
    resource: str
    id_type: Optional[ManagedIdentityIdType] = None
    id_value: Optional[str] = ''
    kwargs: Optional[dict] = None


@dataclass
class ServicePrincipalIdentityProviderConfig:
    client_credential: Any
    client_id: str
    scopes: Optional[List[str]] = None
    timeout: Optional[float] = None
    tenant_id: Optional[str] = None
    token_kwargs: Optional[dict] = None
    app_kwargs: Optional[dict] = None


class EntraIDIdentityProvider(IdentityProviderInterface):
    """
    EntraID Identity Provider implementation.
    It's recommended to use an additional factory methods to simplify object instantiation.

    Methods: create_provider_from_managed_identity, create_provider_from_service_principal.
    """
    def __init__(
            self,
            app: Union[ManagedIdentityClient, ConfidentialClientApplication],
            scopes : List = [],
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


def create_provider_from_managed_identity(config: ManagedIdentityProviderConfig) -> EntraIDIdentityProvider:
    """
    Create an EntraID identity provider following Managed Identity auth flow.

    :param config: Config for managed assigned identity provider
    See: :class:`ManagedIdentityClient` acquire_token_for_client method.

    :return: :class:`EntraIDIdentityProvider`
    """
    if config.identity_type == ManagedIdentityType.USER_ASSIGNED:
        if config.id_type is None or config.id_value == '':
            raise ValueError("Id_type and id_value are required for User Assigned identity auth")

        kwargs = {
            config.id_type.value: config.id_value
        }

        managed_identity = config.identity_type.value(**kwargs)
    else:
        managed_identity = config.identity_type.value()

    app = ManagedIdentityClient(managed_identity, http_client=requests.Session())
    return EntraIDIdentityProvider(app, [], config.resource, **config.kwargs)


def create_provider_from_service_principal(config: ServicePrincipalIdentityProviderConfig) -> EntraIDIdentityProvider:
    """
    Create an EntraID identity provider following Service Principal auth flow.

    :param config: Config for service principal identity provider

    :return: :class:`EntraIDIdentityProvider`
    See: :class:`ConfidentialClientApplication`.
    """

    if config.scopes is None:
        scopes = ["https://redis.azure.com/.default"]
    else:
        scopes = config.scopes

    authority = f"https://login.microsoftonline.com/{config.tenant_id}" \
        if config.tenant_id is not None else config.tenant_id

    app = ConfidentialClientApplication(
        client_id=config.client_id,
        client_credential=config.client_credential,
        timeout=config.timeout,
        authority=authority,
        **config.app_kwargs
    )
    return EntraIDIdentityProvider(app, scopes, **config.token_kwargs)
