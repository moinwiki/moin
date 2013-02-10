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
"""


from MoinMoin import log
logging = log.getLogger(__name__)

from flask import request

from MoinMoin import user
from MoinMoin.i18n import _, L_, N_
from MoinMoin.auth import BaseAuth, GivenAuth


class HTTPAuthMoin(BaseAuth):
    """ authenticate via http (basic) auth """
    name = 'http'

    def __init__(self, autocreate=False, realm='MoinMoin', coding='iso-8859-1', **kw):
        super(HTTPAuthMoin, self).__init__(**kw)
        self.autocreate = autocreate
        self.realm = realm
        self.coding = coding

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
            logging.debug("http basic auth, received username: {0!r} password: {1!r}".format(auth.username, auth.password))
            u = user.User(name=auth.username.decode(self.coding),
                          password=auth.password.decode(self.coding),
                          auth_method=self.name, auth_attribs=[], trusted=self.trusted)
            logging.debug("user: {0!r}".format(u))

        if not u or not u.valid:
            from werkzeug import Response, abort
            response = Response(_('Please log in first.'), 401,
                                {'WWW-Authenticate': 'Basic realm="{0}"'.format(self.realm)})
            abort(response)

        logging.debug("u: {0!r}".format(u))
        if u and self.autocreate:
            logging.debug("autocreating user")
            u.create_or_update()
        if u and u.valid:
            logging.debug("returning valid user {0!r}".format(u))
            return u, True # True to get other methods called, too
        else:
            logging.debug("returning {0!r}".format(user_obj))
            return user_obj, True
