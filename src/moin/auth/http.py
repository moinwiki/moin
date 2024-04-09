# Copyright: 2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - http authentication

    HTTPAuthMoin
    ============

    HTTPAuthMoin is HTTP auth done by moin (not by your web server).

    Moin will request HTTP Basic Auth and use the HTTP Basic Auth header it
    receives to authenticate username/password against the moin user profiles.

    from moin.auth.http import HTTPAuthMoin
    auth = [HTTPAuthMoin()]
"""


from flask import request

from moin import user
from moin.i18n import _
from moin.auth import BaseAuth

from moin import log

logging = log.getLogger(__name__)


class HTTPAuthMoin(BaseAuth):
    """authenticate via http (basic) auth"""

    name = "http"

    def __init__(self, trusted=True, autocreate=False, realm="MoinMoin", coding="utf-8", **kw):
        super().__init__(**kw)
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
            logging.debug(f"http basic auth, received username: {auth.username!r} password: {auth.password!r}")
            u = user.User(
                name=auth.username, password=auth.password, auth_method=self.name, auth_attribs=[], trusted=self.trusted
            )
            logging.debug(f"user: {u!r}")

        if not u or not u.valid:
            from werkzeug import Response
            from werkzeug.exceptions import abort

            response = Response(_("Please log in first."), 401, {"WWW-Authenticate": f'Basic realm="{self.realm}"'})
            abort(response)

        logging.debug(f"u: {u!r}")
        if u and self.autocreate:
            logging.debug("autocreating user")
            u.create_or_update()
        if u and u.valid:
            logging.debug(f"returning valid user {u!r}")
            return u, True  # True to get other methods called, too
        else:
            logging.debug(f"returning {user_obj!r}")
            return user_obj, True
