# Copyright: 2012 MoinMoin:TarashishMishra
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Authentication on GAE

    Users could log in into moin using their google account

"""


from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import user
from MoinMoin.auth import BaseAuth, MultistageRedirectLogin, ContinueLogin
from MoinMoin.constants.keys import *

from werkzeug import redirect, abort
from flask import url_for

from google.appengine.api import users


class GAEAuthMoin(BaseAuth):
    """ authenticate on gae using google account """
    name = 'gae'
    login_inputs = ['special_no_input']
    logout_possible = True

    def login(self, user_obj=None, **kw):
        u = None
        # always revalidate auth
        if user_obj and user_obj.auth_method == self.name:
            user_obj = None
        # something else authenticated before us
        if user_obj:
            return ContinueLogin(user_obj)
        # get the current user from gae
        gae_user = users.get_current_user()
        if not gae_user:
            # Redirect the user to the google account login, telling it to redirect back to
            # moin's .show_root url, simulating a login there.
            return_to = url_for(".show_root", login_submit=1)
            return MultistageRedirectLogin(users.create_login_url(return_to))

        gae_user_id = unicode(gae_user.user_id())
        email = unicode(gae_user.email())
        nickname = unicode(gae_user.nickname())
        logging.debug("Current gae_user: name: {0!r}, email: {1!r}, gae_user_id: {2!r}".format(nickname, email, gae_user_id))
        # try to get existing user with the same gae_user_id
        users_list = user.search_users(gae_user_id=gae_user_id)
        if users_list:
            u = user.User(uid=users_list[0].meta[ITEMID], trusted=self.trusted, auth_method=self.name)
            changed = False
        else:
            # if no user with same gae_user_id found try to get existing user with the same email
            users_list = user.search_users(email=email)
            if users_list:
                u = user.User(uid=users_list[0].meta[ITEMID], trusted=self.trusted, auth_method=self.name)
                # set gae_user_id when user is found by email
                u.profile[GAE_USER_ID] = gae_user_id
                changed = True
            else:
                # if there is no existing user with same gae_user_id or email create one
                u = user.User(trusted=self.trusted, auth_method=self.name)
                u.profile[GAE_USER_ID] = gae_user_id
                u.profile[EMAIL] = email
                u.profile[NAME] = nickname
                changed = True
        if u:
            u.create_or_update(changed=changed)
            user_obj = u

        return ContinueLogin(user_obj)

    def logout(self, user_obj, **kw):
        # TODO: currently, logging out of moin logs you out of all applications that use your
        # google account. We should fix that.
        user_obj.logout_session()
        abort(redirect(users.create_logout_url(url_for('.show_root'))))
