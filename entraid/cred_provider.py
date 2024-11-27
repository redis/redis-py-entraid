from typing import Self, Union, Tuple, Callable, Any

from redis.credentials import StreamingCredentialProvider
from redisauth.token_manager import TokenManagerConfig, RetryPolicy, TokenManager, CredentialsListener

from entraid.identity_provider import EntraIDIdentityProvider


class TokenAuthConfig:
    def __init__(self):
        self._expiration_refresh_ratio = 1.0
        self._lower_refresh_bound_millis = 0
        self._token_request_execution_timeout_in_ms = 100
        self._max_attempts = 3
        self._delay_in_ms = 10
        self._identity_provider_config = {
            "scopes": ["https://redis.azure.com/.default"],
            "config": {},
        }

    def get_token_manager_config(self) -> TokenManagerConfig:
        return TokenManagerConfig(
            self._expiration_refresh_ratio,
            self._lower_refresh_bound_millis,
            self._token_request_execution_timeout_in_ms,
            RetryPolicy(
                self._max_attempts,
                self._delay_in_ms
            )
        )

    def get_identity_provider_config(self) -> dict:
        return self._identity_provider_config

    def expiration_refresh_ratio(self, value: float) -> Self:
        """
        Percentage value of total token TTL when refresh should be triggered.
        Default: 1.0

        :param value: float
        :return: Self
        """
        self._expiration_refresh_ratio = value
        return self

    def lower_refresh_bound_millis(self, value: int) -> Self:
        """
        Represents the minimum time in milliseconds before token expiration to trigger a refresh, in milliseconds.
        Default: 0

        :param value: int
        :return: Self
        """
        self._lower_refresh_bound_millis = value
        return self

    def token_request_execution_timeout_in_ms(self, value: int) -> Self:
        """
        Represents the maximum time in milliseconds to wait for a token request to complete.
        Default: 100

        :param value: int
        :return: Self
        """
        self._token_request_execution_timeout_in_ms = value
        return self

    def max_attempts(self, value: int) -> Self:
        """
        Represents the maximum number of attempts to trigger a refresh in case of error.
        Default: 3

        :param value: int
        :return: Self
        """
        self._max_attempts = value
        return self

    def delay_in_ms(self, value: int) -> Self:
        """
        Represents the delay between retries.
        Default: 10

        :param value: int
        :return: Self
        """
        self._delay_in_ms = value
        return self

    def identity_provider_config(self, value: dict) -> Self:
        """
        Identity provider specific configuration as dictionary.

        :param value: "Scopes" key is required. "Config" key represents the actual configuration.
        :return: Self
        """

        if value.get("scopes", None) is None:
            raise ValueError("Scope key is required")

        self._identity_provider_config = value
        return self


class EntraIdCredentialsProvider(StreamingCredentialProvider):
    def __init__(self, config: TokenAuthConfig):
        self._token_mgr = TokenManager(
            EntraIDIdentityProvider(
                config.get_identity_provider_config().get('scopes'),
                **config.get_identity_provider_config().get('config')
            ),
            config.get_token_manager_config()
        )
        self._listener = CredentialsListener()
        self._is_streaming = False

    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        if self._listener is None:
            raise Exception('To obtain the credentials the listener must be set first')

        init_token = self._token_mgr.acquire_token()

        if self._is_streaming is False:
            self._token_mgr.start(
                self._listener
            )
            self._is_streaming = True

        return init_token.get_token().try_get('oid'), init_token.get_token().get_value()

    def on_next(self, callback: Callable[[Any], None]):
        self._listener.on_next = callback

    def on_error(self, callback: Callable[[Exception], None]):
        self._listener.on_error = callback

    def is_streaming(self) -> bool:
        return self._is_streaming
