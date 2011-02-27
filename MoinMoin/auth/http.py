# Copyright: 2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - http authentication

    HTTPAuthMoin
    ============

    HTTPAuthMoin is HTTP auth done by moin (not by your web server).

    Moin will request HTTP Basic Auth and use the HTTP Basic Auth header it
    receives to authenticate username/password against the moin user profiles.

    from MoinMoin.auth.http import HTTPAuthMoin
    auth = [HTTPAuthMoin()]
    # check if you want 'http' auth name in there:
    auth_methods_trusted = ['http', ]
"""


from MoinMoin import log
logging = log.getLogger(__name__)

from flask import request

from MoinMoin import config, user
from MoinMoin.i18n import _, L_, N_
from MoinMoin.auth import BaseAuth, GivenAuth


class HTTPAuthMoin(BaseAuth):
    """ authenticate via http (basic) auth """
    name = 'http'

    def __init__(self, autocreate=False, realm='MoinMoin', coding='iso-8859-1'):
        self.autocreate = autocreate
        self.realm = realm
        self.coding = coding
        BaseAuth.__init__(self)

    def request(self, user_obj, **kw):
        u = None
        # always revalidate auth
        if user_obj and user_obj.auth_method == self.name:
            user_obj = None
        # something else authenticated before us
        if user_obj:
            return user_obj, True

        auth = request.authorization
        if auth and auth.username and auth.password is not None:
            logging.debug("http basic auth, received username: %r password: %r" % (
                          auth.username, auth.password))
            u = user.User(name=auth.username.decode(self.coding),
                          password=auth.password.decode(self.coding),
                          auth_method=self.name, auth_attribs=[])
            logging.debug("user: %r" % u)

        if not u or not u.valid:
            from werkzeug import Response, abort
            response = Response(_('Please log in first.'), 401,
                                {'WWW-Authenticate': 'Basic realm="%s"' % self.realm})
            abort(response)

        logging.debug("u: %r" % u)
        if u and self.autocreate:
            logging.debug("autocreating user")
            u.create_or_update()
        if u and u.valid:
            logging.debug("returning valid user %r" % u)
            return u, True # True to get other methods called, too
        else:
            logging.debug("returning %r" % user_obj)
            return user_obj, True

