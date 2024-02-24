from flask_pyoidc import OIDCAuthentication
from flask_pyoidc.provider_configuration import ClientMetadata, ProviderConfiguration

from wikiconfig import OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_LOGOUT_URI


oidc = OIDCAuthentication({
    'idp': ProviderConfiguration(
        issuer=OIDC_ISSUER,
        # static client registration
        client_metadata=ClientMetadata(
            client_id=OIDC_CLIENT_ID,
            client_secret=OIDC_CLIENT_SECRET,
            post_logout_redirect_uris=[OIDC_LOGOUT_URI],
        ),
    ),
})
