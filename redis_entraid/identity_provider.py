from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, List, Tuple, Iterable

import requests
from azure.identity import DefaultAzureCredential
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
    kwargs: Optional[dict] = field(default_factory=dict)


@dataclass
class ServicePrincipalIdentityProviderConfig:
    client_credential: Any
    client_id: str
    scopes: Optional[List[str]] = None
    timeout: Optional[float] = None
    tenant_id: Optional[str] = None
    token_kwargs: Optional[dict] = field(default_factory=dict)
    app_kwargs: Optional[dict] = field(default_factory=dict)


@dataclass
class DefaultAzureCredentialIdentityProviderConfig:
    scopes: Iterable[str]
    additional_tenant_id: Optional[str] = None
    authority: Optional[str] = None
    token_kwargs: Optional[dict] = field(default_factory=dict)
    app_kwargs: Optional[dict] = field(default_factory=dict)


class ManagedIdentityProvider(IdentityProviderInterface):
    """
    Identity Provider implementation for Azure Managed Identity auth type.
    """
    def __init__(
            self,
            app: ManagedIdentityClient,
            resource: str,
            **kwargs
    ):
        """
        :param kwargs: See: :class:`ManagedIdentityClient` for additional configuration.
        """
        self._app = app
        self._resource = resource
        self._kwargs = kwargs

    def request_token(self, force_refresh=False) -> TokenInterface:
        """
        Request token from identity provider. Force refresh isn't supported for this provider type.
        """
        try:
            response = self._app.acquire_token_for_client(resource=self._resource, **self._kwargs)

            if "error" in response:
                raise RequestTokenErr(response["error_description"])
        except Exception as e:
            raise RequestTokenErr(e)

        return JWToken(response["access_token"])


class ServicePrincipalProvider(IdentityProviderInterface):
    """
    Identity Provider implementation for Azure Service Principal auth type.
    """
    def __init__(
            self,
            app: ConfidentialClientApplication,
            scopes: Optional[List[str]] = None,
            **kwargs
    ):
        """
        :param kwargs: See: :class:`ConfidentialClientApplication` for additional configuration.
        """
        self._app = app
        self._scopes = scopes
        self._kwargs = kwargs

    def request_token(self, force_refresh=False) -> TokenInterface:
        """
        Request token from identity provider.
        """
        if force_refresh:
            self._app.remove_tokens_for_client()

        try:
            response = self._app.acquire_token_for_client(scopes=self._scopes, **self._kwargs)

            if "error" in response:
                raise RequestTokenErr(response["error_description"])
        except Exception as e:
            raise RequestTokenErr(e)

        return JWToken(response["access_token"])


class DefaultAzureCredentialProvider(IdentityProviderInterface):
    """
    Identity Provider implementation for Default Azure Credential flow.
    """

    def __init__(
            self,
            app: DefaultAzureCredential,
            scopes: Tuple[str],
            additional_tenant_id: Optional[str] = None,
            **kwargs
    ):
        self._app = app
        self._scopes = scopes
        self._additional_tenant_id = additional_tenant_id
        self._kwargs = kwargs

    def request_token(self, force_refresh=False) -> TokenInterface:
        try:
            response = self._app.get_token(*self._scopes, tenant_id=self._additional_tenant_id, **self._kwargs)
        except Exception as e:
            raise RequestTokenErr(e)

        return JWToken(response.token)


def _create_provider_from_managed_identity(config: ManagedIdentityProviderConfig) -> ManagedIdentityProvider:
    """
    Create a Managed identity provider following Managed Identity auth flow.

    :param config: Config for managed assigned identity provider
    See: :class:`ManagedIdentityClient` acquire_token_for_client method.

    :return: :class:`ManagedIdentityProvider`
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
    return ManagedIdentityProvider(app, config.resource, **config.kwargs)


def _create_provider_from_service_principal(config: ServicePrincipalIdentityProviderConfig) -> ServicePrincipalProvider:
    """
    Create a Service Principal identity provider following Service Principal auth flow.

    :param config: Config for service principal identity provider

    :return: :class:`ServicePrincipalProvider`
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
    return ServicePrincipalProvider(app, scopes, **config.token_kwargs)


def _create_provider_from_default_azure_credential(
        config: DefaultAzureCredentialIdentityProviderConfig
) -> DefaultAzureCredentialProvider:
    """
    Create a Default Azure Credential identity provider following Default Azure Credential flow.

    :param config: Config for default Azure Credential identity provider
    :return: :class:`DefaultAzureCredentialProvider`
    See: :class:`DefaultAzureCredential`.
    """

    app = DefaultAzureCredential(
        authority=config.authority,
        **config.app_kwargs
    )

    return DefaultAzureCredentialProvider(app, config.scopes, config.additional_tenant_id, **config.token_kwargs)
