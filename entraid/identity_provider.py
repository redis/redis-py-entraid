from msal import ConfidentialClientApplication
from redisauth.err import RequestTokenErr
from redisauth.idp import IdentityProviderInterface
from redisauth.token import TokenInterface, JWToken


class EntraIDIdentityProvider(IdentityProviderInterface):
    def __init__(self, scopes : list = [], **kwargs):
        self._app = ConfidentialClientApplication(**kwargs)
        self._scopes = scopes

    def request_token(self) -> TokenInterface:
        try:
            return JWToken(
                self._app.acquire_token_for_client(self._scopes)["access_token"]
            )
        except Exception as e:
            raise RequestTokenErr(e)