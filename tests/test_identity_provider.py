import pytest
from msal import TokenCache

from redis_entraid.identity_provider import EntraIDIdentityProvider


class TestEntraIDIdentityProvider:
    CUSTOM_CACHE = TokenCache()

    def test_request_token_from_service_principal_identity(self, identity_provider: EntraIDIdentityProvider):
        assert identity_provider.request_token(force_refresh=True)

    @pytest.mark.parametrize(
        "identity_provider",
        [
            {
                "idp_kwargs": {"token_cache": CUSTOM_CACHE},
            }
        ],
        indirect=True,
    )
    def test_request_token_caches_token_after_initial_request(self, identity_provider):
        assert len(list(self.CUSTOM_CACHE.search(TokenCache.CredentialType.ACCESS_TOKEN))) == 0

        token = identity_provider.request_token()
        assert len(list(self.CUSTOM_CACHE.search(TokenCache.CredentialType.ACCESS_TOKEN))) == 1
        assert list(self.CUSTOM_CACHE.search(
            TokenCache.CredentialType.ACCESS_TOKEN
        ))[0].get('secret') == token.get_value()

        identity_provider.request_token()
        assert len(list(self.CUSTOM_CACHE.search(TokenCache.CredentialType.ACCESS_TOKEN))) == 1
        assert list(self.CUSTOM_CACHE.search(
            TokenCache.CredentialType.ACCESS_TOKEN
        ))[0].get('secret') == token.get_value()

        new_token = identity_provider.request_token(force_refresh=True)
        assert token.get_value() != new_token.get_value()
        assert len(list(self.CUSTOM_CACHE.search(TokenCache.CredentialType.ACCESS_TOKEN))) == 1
        assert list(self.CUSTOM_CACHE.search(
            TokenCache.CredentialType.ACCESS_TOKEN
        ))[0].get('secret') == new_token.get_value()
