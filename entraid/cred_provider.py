from typing import Self, Union, Tuple, Callable, Any, Awaitable

from redis.credentials import StreamingCredentialProvider
from redis.auth.token_manager import TokenManagerConfig, RetryPolicy, TokenManager, CredentialsListener

from entraid.identity_provider import EntraIDIdentityProvider


class TokenAuthConfig:
    """
    Configuration for token authentication.

    Requires :class:`EntraIDIdentityProvider`. It's recommended to use an additional factory methods.
    See :class:`EntraIDIdentityProvider` for more information.
    """
    DEFAULT_EXPIRATION_REFRESH_RATIO = 0.8
    DEFAULT_LOWER_REFRESH_BOUND_MILLIS = 0
    DEFAULT_TOKEN_REQUEST_EXECUTION_TIMEOUT_IN_MS = 100
    DEFAULT_MAX_ATTEMPTS = 3
    DEFAULT_DELAY_IN_MS = 3

    def __init__(self, idp: EntraIDIdentityProvider):
        self._expiration_refresh_ratio = self.DEFAULT_EXPIRATION_REFRESH_RATIO
        self._lower_refresh_bound_millis = self.DEFAULT_LOWER_REFRESH_BOUND_MILLIS
        self._token_request_execution_timeout_in_ms = self.DEFAULT_TOKEN_REQUEST_EXECUTION_TIMEOUT_IN_MS
        self._max_attempts = self.DEFAULT_MAX_ATTEMPTS
        self._delay_in_ms = self.DEFAULT_DELAY_IN_MS
        self._idp = idp

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

    def get_identity_provider(self) -> EntraIDIdentityProvider:
        return self._idp

    def expiration_refresh_ratio(self, value: float) -> Self:
        """
        Percentage value of total token TTL when refresh should be triggered.
        Default: 0.8

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


class EntraIdCredentialsProvider(StreamingCredentialProvider):
    def __init__(
            self,
            config: TokenAuthConfig,
            initial_delay_in_ms: float = 0,
            block_for_initial: bool = False,
    ):
        """
        :param config:
        :param initial_delay_in_ms: Initial delay before run background refresh (valid for async only)
        :param block_for_initial: Block execution until initial token will be acquired (valid for async only)
        """
        self._token_mgr = TokenManager(
            config.get_identity_provider(),
            config.get_token_manager_config()
        )
        self._listener = CredentialsListener()
        self._is_streaming = False
        self._initial_delay_in_ms = initial_delay_in_ms
        self._block_for_initial = block_for_initial

    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        init_token = self._token_mgr.acquire_token()

        if self._is_streaming is False:
            self._token_mgr.start(
                self._listener,
                skip_initial=True
            )
            self._is_streaming = True

        return init_token.get_token().try_get('oid'), init_token.get_token().get_value()

    async def get_credentials_async(self) -> Union[Tuple[str], Tuple[str, str]]:
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
