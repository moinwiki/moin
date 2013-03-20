# Copyright: 2006-2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - logging auth plugin

    This does nothing except logging the auth parameters (the password is NOT
    logged, of course).
"""


from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.auth import BaseAuth, ContinueLogin


class AuthLog(BaseAuth):
    """ just log the call, do nothing else """
    name = "log"

    def __init__(self, **kw):
        super(AuthLog, self).__init__(**kw)

    def log(self, action, user_obj, kw):
        logging.info('{0}: user_obj={1!r} kw={2!r}'.format(action, user_obj, kw))

    def login(self, user_obj, **kw):
        self.log('login', user_obj, kw)
        return ContinueLogin(user_obj)

    def request(self, user_obj, **kw):
        self.log('session', user_obj, kw)
        return user_obj, True

    def logout(self, user_obj, **kw):
        self.log('logout', user_obj, kw)
        return user_obj, True
