from entraid.identity_provider import create_provider_from_managed_identity, ManagedIdentityType


def main():
    provider = create_provider_from_managed_identity(
        ManagedIdentityType.SYSTEM_ASSIGNED,
        "https://redis.azure.com"
    )

    print(provider.request_token().get_value())


if __name__ == "__main__":
    main()

