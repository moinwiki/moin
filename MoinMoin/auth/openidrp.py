# Copyright: 2010 MoinMoin:Nichita Utiu
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - OpenID authentication

    This code handles login requests for openid multistage authentication.
"""


from MoinMoin import log
logging = log.getLogger(__name__)

from openid.store.memstore import MemoryStore
from openid.consumer import consumer
from openid.yadis.discover import DiscoveryFailure
from openid.fetchers import HTTPFetchingError

from flask import session, request, url_for
from flask import current_app as app
from MoinMoin.auth import BaseAuth, get_multistage_continuation_url
from MoinMoin.auth import ContinueLogin, CancelLogin, MultistageFormLogin, MultistageRedirectLogin
from MoinMoin.config import ITEMID
from MoinMoin import user
from MoinMoin.i18n import _, L_, N_


class OpenIDAuth(BaseAuth):
    def __init__(self, trusted_providers=[], **kw):
        super(OpenIDAuth, self).__init__(**kw)
        # the name
        self.name = 'openid'
        # we only need openid
        self.login_inputs = ['openid']
        # logout is possible
        self.logout_possible = True
        # the store
        self.store = MemoryStore()

        self._trusted_providers = list(trusted_providers)

    def _handleContinuationVerify(self):
        """
        Handles the first stage continuation.
        """
        # the consumer object with an in-memory storage
        oid_consumer = consumer.Consumer(session, self.store)

        # a dict containing the parsed query string
        query = {}
        for key in request.values.keys():
            query[key] = request.values.get(key)
        # the current url (w/o query string)
        url = get_multistage_continuation_url(self.name, {'oidstage': '1'})

        # we get the info about the authentication
        oid_info = oid_consumer.complete(query, url)
        # the identity we've retrieved from the response
        if oid_info.status == consumer.FAILURE:
            # verification has failed
            # return an error message with description of error
            logging.debug("OpenIDError: {0}".format(oid_info.message))

            error_message = _('OpenID Error')
            return CancelLogin(error_message)
        elif oid_info.status == consumer.CANCEL:
            logging.debug("OpenID verification cancelled.")

            # verification was cancelled
            # return error
            return CancelLogin(_('OpenID verification cancelled.'))
        elif oid_info.status == consumer.SUCCESS:
            logging.debug('OpenID success. id: {0}'.format(oid_info.identity_url))

            # we get the provider's url
            # and the list of trusted providers
            trusted = self._trusted_providers
            server = oid_info.endpoint.server_url

            if server in trusted or not trusted:
                # the provider is trusted or all providers are trusted
                # we have successfully authenticated our openid
                # we get the user with this openid associated to him
                identity = oid_info.identity_url
                users = user.search_users(openid=identity)
                user_obj = users and user.User(users[0][ITEMID], trusted=self.trusted)

                # if the user actually exists
                if user_obj:
                    # we get the authenticated user object
                    # success!
                    user_obj.auth_method = self.name
                    return ContinueLogin(user_obj)

                # there is no user with this openid
                else:
                    # redirect the user to registration
                    return MultistageRedirectLogin(url_for('frontend.register',
                                                           _external=True,
                                                           openid_openid=identity,
                                                           openid_submit='1'
                                                          ))

            # not trusted
            return ContinueLogin(None, _('This OpenID provider is not trusted.'))

        else:
            logging.debug("OpenID failure")
            # the auth failed miserably
            return CancelLogin(_('OpenID failure.'))

    def _handleContinuation(self):
        """
        Handles continuations appropriately.
        """
        # the current stage
        oidstage = request.values.get('oidstage')
        if oidstage == '1':
            return self._handleContinuationVerify()
        # more can be added for extended functionality

    def login(self, userobj, **kw):
        """
        Handles an login request and continues to multistage continuation
        if necessary.
        """
        continuation = kw.get('multistage')
        # process another subsequent step
        if continuation:
            return self._handleContinuation()

        openid = kw.get('openid')
        # no openid entered
        if not openid:
            return ContinueLogin(userobj)

        # we make a consumer object with an in-memory storage
        oid_consumer = consumer.Consumer(session, self.store)

        # we catch any possible openid-related exceptions
        try:
            oid_response = oid_consumer.begin(openid)
        except HTTPFetchingError:
            return ContinueLogin(None, _('Failed to resolve OpenID.'))
        except DiscoveryFailure:
            return ContinueLogin(None, _('OpenID discovery failure, not a valid OpenID.'))
        else:
            # we got no response from the service
            if oid_response is None:
                return ContinueLogin(None, _('No OpenID service at this URL.'))

            # site root and where to return after the redirect
            site_root = url_for('frontend.show_root', _external=True)
            return_to = get_multistage_continuation_url(self.name, {'oidstage': '1'})

            # should we redirect the user?
            if oid_response.shouldSendRedirect():
                redirect_url = oid_response.redirectURL(site_root, return_to)
                return MultistageRedirectLogin(redirect_url)
            else:
                # send a form
                form_html = oid_response.htmlMarkup(site_root, return_to, form_tag_attrs={'id': 'openid_message'})

                # returns a MultistageFormLogin
                return MultistageFormLogin(form_html)

