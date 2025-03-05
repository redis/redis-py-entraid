# Before run this example you need to configure your EntraID application the following way:
#
# 1. Enable "Allow public client flows" option, under "Authentication" section.
# 2. Add the Redirect URL of the web server that DefaultAzureCredential runs
# By default, uses port 8400, so the default Redirect URL looks like "http://localhost:8400".

import os

from redis_entraid.cred_provider import create_from_default_azure_credential

def main():

    # By default, interactive browser login is excluded so you need to enable it.
    credential_provider = create_from_default_azure_credential(
        ("user.read",),
        app_kwargs={
            "exclude_interactive_browser_credential": False,
            "interactive_browser_client_id": os.getenv("AZURE_CLIENT_ID"),
            "interactive_browser_tenant_id": os.getenv("AZURE_TENANT_ID"),
        }
    )

    # Opens a browser tab. After you'll enter your username/password it would return you a credentials needed for auth.
    print(credential_provider.get_credentials())


if __name__ == "__main__":
    main()