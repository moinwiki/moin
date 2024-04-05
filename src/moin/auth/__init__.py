# Copyright: 2005-2006 Bastian Blank, Florian Festi
# Copyright: MoinMoin:AlexanderSchremmer, Nick Phillips
# Copyright: MoinMoin:FrankieChow, MoinMoin:NirSoffer
# Copyright: 2005-2012 MoinMoin:ThomasWaldmann
# Copyright: 2007      MoinMoin:JohannesBerg
# Copyright: 2023-2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - modular authentication handling

Each authentication method is an object instance containing
four methods:

    * ``login(user_obj, **kw)``
    * ``logout(user_obj, **kw)``
    * ``request(user_obj, **kw)``
    * ``login_hint()``

The kw arguments that are passed in are currently:

    attended: boolean indicating whether a user (attended=True) or
                a machine is requesting login, multistage auth is not
                currently possible for machine logins [login only]
    username: the value of the 'username' form field (or None)
                [login only]
    password: the value of the 'password' form field (or None)
                [login only]
    cookie: a Cookie.SimpleCookie instance containing the cookie
            that the browser sent
    multistage: boolean indicating multistage login continuation
                [may not be present, login only]

login_hint() should return a HTML text that is displayed to the user right
below the login form, it should tell the user what to do in case of a
forgotten password and how to create an account (if applicable.)

More may be added.

The request method is called for each request except login/logout.

The 'request' and 'logout' methods must return a tuple (user_obj, continue)
where 'user_obj' can be:

    * None, to throw away any previous user_obj from previous auth methods
    * the passed in user_obj for no changes
    * a newly created moin.user.User instance

and 'continue' is a boolean to indicate whether the next authentication
method should be tried.

The 'login' method must return an instance of moin.auth.LoginReturn
which contains the members:

    * user_obj
    * continue_flag
    * multistage
    * message
    * redirect_to

There are some helpful subclasses derived from this class for the most
common cases, namely ContinueLogin(), CancelLogin(), MultistageFormLogin()
and MultistageRedirectLogin().

The user_obj and continue_flag members have the same semantics as for the
request and logout methods.

The messages that are returned by the various auth methods will be
displayed to the user, since they will all be displayed usually auth
methods will use the message feature only along with returning False for
the continue flag.

Note, however, that when no username is entered or the username is not
found in the database, it may be appropriate to return with a message
and the continue flag set to true (ContinueLogin) because a subsequent auth
plugin might work even without the username.

The multistage member must evaluate to false or be callable. If it is
callable, this indicates that the authentication method requires a second
login stage. In that case, the multistage item will be called and should
return an instance of
moin.widget.html.FORM and the generic code will append some required
hidden fields to it. It is also permissible to return some valid HTML,
but that feature has very limited use since it breaks the authentication
method chain.

Note that because multistage login does not depend on anonymous session
support, it is possible that users jump directly into the second stage
by giving the appropriate parameters to the login action. Hence, auth
methods should take care to recheck everything and not assume the user
has gone through all previous stages.

If the multistage login requires querying an external site that involves
a redirect, the redirect_to member may be set instead of the multistage
member. If this is set it must be a URL that user should be redirected to.
Since the user must be able to come back to the authentication, any
"%return" in the URL is replaced with the url-encoded form of the URL
to the next authentication stage, any "%return_form" is replaced with
the url-plus-encoded form (spaces encoded as +) of the same URL.

After the user has submitted the required form or has been redirected back
from the external site, execution of the auth login methods resumes with
the auth item that requested the multistage login and its login method is
called with the 'multistage' keyword parameter set to True.

Each authentication method instance must also contain the members:

    * login_inputs: a list of required inputs, currently supported are
                    - 'username': username entry field
                    - 'password': password entry field
                    - 'special_no_input': manual login is required
                        but no form fields need to be filled in
                        in this case the theme may provide a short-
                        cut omitting the login form
    * logout_possible: boolean indicating whether this auth methods
                    supports logging out
    * name: name of the auth method, must be the same as given as the
            user object's auth_method keyword parameter.

To simplify creating new authentication methods you can inherit from
moin.auth.BaseAuth that does nothing for all three methods, but
allows you to override only some methods.

cfg.auth is a list of authentication object instances whose methods
are called in the order they are listed. The session method is called
for every request, when logging in or out these are called before the
session method.

When creating a new moin.user.User object, you can give a keyword
argument "auth_attribs" to User.__init__ containing a list of user
attributes that are determined and fixed by this auth method and may
not be changed by the user in their preferences.
You also have to give the keyword argument "auth_method" containing the
name of the authentication method.
"""

from urllib.parse import quote, quote_plus
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from flask import url_for, session, request
from flask import g as flaskg
from flask import current_app as app
from markupsafe import Markup

from moin import user
from moin.i18n import _

from moin import log

logging = log.getLogger(__name__)


def get_multistage_continuation_url(auth_name, extra_fields={}):
    """
    get_continuation_url - return a multistage continuation URL

    This function returns a URL that when loaded continues a multistage
    authentication at the auth method requesting it (parameter auth_name.)
    Additional fields are added to the URL from the extra_fields dict.

    :param auth_name: name of the auth method requesting the continuation
    :param extra_fields: extra GET fields to add to the URL
    """
    # logically, this belongs to request, but semantically it should
    # live in auth so people do auth.get_multistage_continuation_url()

    # the url should be absolute so we use _external
    url = url_for("frontend.login", login_submit="1", stage=auth_name, _external=True, **extra_fields)
    logging.debug(f"multistage_continuation_url: {url}")
    return url


class LoginReturn:
    """LoginReturn - base class for auth method login() return value"""

    def __init__(self, user_obj, continue_flag, message=None, multistage=None, redirect_to=None):
        self.user_obj = user_obj
        self.continue_flag = continue_flag
        self.message = message
        self.multistage = multistage
        self.redirect_to = redirect_to


class ContinueLogin(LoginReturn):
    """ContinueLogin - helper for auth method login that just continues"""

    def __init__(self, user_obj, message=None):
        LoginReturn.__init__(self, user_obj, True, message=message)


class CancelLogin(LoginReturn):
    """CancelLogin - cancel login showing a message"""

    def __init__(self, message):
        LoginReturn.__init__(self, None, False, message=message)


class MultistageFormLogin(LoginReturn):
    """MultistageFormLogin - require user to fill in another form"""

    def __init__(self, multistage):
        LoginReturn.__init__(self, None, False, multistage=multistage)


class MultistageRedirectLogin(LoginReturn):
    """MultistageRedirectLogin - redirect user to another site before continuing login"""

    def __init__(self, url):
        LoginReturn.__init__(self, None, False, redirect_to=url)


class BaseAuth:
    name = None
    login_inputs = []
    logout_possible = False

    def __init__(self, trusted=False, **kw):
        self.trusted = trusted
        if kw:
            raise TypeError(f"got unexpected arguments {kw!r}")

    def login(self, user_obj, **kw):
        return ContinueLogin(user_obj)

    def request(self, user_obj, **kw):
        return user_obj, True

    def logout(self, user_obj, **kw):
        if self.name and user_obj and user_obj.auth_method == self.name:
            logging.debug(f"{self.name}: logout - invalidating user {user_obj.name!r}")
            user_obj.valid = False
        return user_obj, True

    def login_hint(self):
        return None


class MoinAuth(BaseAuth):
    """handle login from moin login form"""

    def __init__(self, **kw):
        super().__init__(**kw)

    login_inputs = ["username", "password"]
    name = "moin"
    logout_possible = True

    def login(self, user_obj, **kw):
        username = kw.get("username")
        password = kw.get("password")

        # simply continue if something else already logged in successfully
        if user_obj and user_obj.valid:
            return ContinueLogin(user_obj)

        if not username and not password:
            return ContinueLogin(user_obj)

        logging.debug(f"{self.name}: performing login action")

        if username and not password:
            return ContinueLogin(user_obj, _("Missing password. Please enter user name and password."))

        u = user.User(name=username, password=password, auth_method=self.name, trusted=self.trusted)
        if u.valid:
            logging.debug(f"{self.name}: successfully authenticated user {u.name!r} (valid)")
            return ContinueLogin(u)
        else:
            logging.debug(f"{self.name}: could not authenticate user {username!r} (not valid)")
            return ContinueLogin(user_obj, _("Invalid username or password."))

    def login_hint(self):
        if app.cfg.registration_only_by_superuser:
            msg = app.cfg.registration_hint + " "
        else:
            msg = _('If you do not have an account, <a href="{register_url}">you can create one now</a>. ').format(
                register_url=url_for("frontend.register")
            )
        msg += _('<a href="{recover_url}">Forgot your password?</a>').format(recover_url=url_for("frontend.lostpass"))
        return Markup(msg)


class GivenAuth(BaseAuth):
    """reuse a given authentication, e.g. http basic auth (or any other auth)
    done by the web server, that sets REMOTE_USER environment variable.
    This is the default behaviour.
    You can also specify to read another environment variable (env_var).
    Alternatively you can directly give a fixed user name (user_name)
    that will be considered as authenticated.
    """

    name = "given"  # was 'http' in 1.8.x and before

    def __init__(
        self,
        env_var=None,  # environment variable we want to read (default: REMOTE_USER)
        user_name=None,  # can be used to just give a specific user name to log in
        autocreate=False,  # create/update the user profile for the auth. user
        strip_maildomain=False,  # joe@example.org -> joe
        strip_windomain=False,  # DOMAIN\joe -> joe
        titlecase=False,  # joe doe -> Joe Doe
        remove_blanks=False,  # Joe Doe -> JoeDoe
        coding="utf-8",  # for decoding REMOTE_USER correctly
        **kw,
    ):
        super().__init__(**kw)
        self.env_var = env_var
        self.user_name = user_name
        self.autocreate = autocreate
        self.strip_maildomain = strip_maildomain
        self.strip_windomain = strip_windomain
        self.titlecase = titlecase
        self.remove_blanks = remove_blanks
        self.coding = coding

    def decode_username(self, name):
        """decode the name we got from the environment var to unicode"""
        if isinstance(name, bytes):
            name = name.decode(self.coding)
        return name

    def transform_username(self, name):
        """transform the name we got (unicode in, unicode out)

        Note: if you need something more special, you could create your own
              auth class, inherit from this class and overwrite this function.
        """
        assert isinstance(name, str)
        if self.strip_maildomain:
            # split off mail domain, e.g. "user@example.org" -> "user"
            name = name.split("@")[0]

        if self.strip_windomain:
            # split off window domain, e.g. "DOMAIN\user" -> "user"
            name = name.split("\\")[-1]

        if self.titlecase:
            # this "normalizes" the login name, e.g. meier, Meier, MEIER -> Meier
            name = name.title()

        if self.remove_blanks:
            # remove blanks e.g. "Joe Doe" -> "JoeDoe"
            name = "".join(name.split())

        return name

    def request(self, user_obj, **kw):
        u = None
        # always revalidate auth
        if user_obj and user_obj.auth_method == self.name:
            user_obj = None
        # something else authenticated before us
        if user_obj:
            logging.debug("already authenticated, doing nothing")
            return user_obj, True

        if self.user_name is not None:
            auth_username = self.user_name
        elif self.env_var is None:
            auth_username = request.remote_user
        else:
            auth_username = request.environ.get(self.env_var)

        logging.debug(f"auth_username = {auth_username!r}")
        if auth_username:
            auth_username = self.decode_username(auth_username)
            auth_username = self.transform_username(auth_username)
            logging.debug(f"auth_username (after decode/transform) = {auth_username!r}")
            u = user.User(
                auth_username=auth_username,
                auth_method=self.name,
                auth_attribs=("name", "password"),
                trusted=self.trusted,
            )

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


def handle_login(userobj, **kw):
    """
    Process a 'login' request by going through the configured authentication
    methods in turn. The passable keyword arguments are explained in more
    detail at the top of this file.
    """

    stage = kw.get("stage")
    params = {
        "username": kw.get("login_username"),
        "password": kw.get("login_password"),
        "multistage": (stage and True) or None,
        "attended": True,
    }
    # add the other parameters from the form
    for param in kw.keys():
        params[param] = kw.get(param)

    for authmethod in app.cfg.auth:
        if stage and authmethod.name != stage:
            continue
        ret = authmethod.login(userobj, **params)

        userobj = ret.user_obj
        cont = ret.continue_flag
        if stage:
            stage = None
            del params["multistage"]

        if ret.multistage:
            flaskg._login_multistage = ret.multistage
            flaskg._login_multistage_name = authmethod.name
            return userobj

        if ret.redirect_to:
            nextstage = get_multistage_continuation_url(authmethod.name)
            url = ret.redirect_to
            url = url.replace("%return_form", quote_plus(nextstage))
            url = url.replace("%return", quote(nextstage))
            abort(redirect(url))
        msg = ret.message
        if msg and msg not in flaskg._login_messages:
            flaskg._login_messages.append(msg)

        if not cont:
            break

    return userobj


def handle_logout(userobj):
    """Logout the passed user from every configured authentication method."""
    if userobj is None:
        # not logged in
        return userobj

    for authmethod in app.cfg.auth:
        userobj, cont = authmethod.logout(userobj)
        if not cont:
            break
    return userobj


def handle_request(userobj):
    """Handle the per-request callbacks of the configured authentication methods."""
    for authmethod in app.cfg.auth:
        userobj, cont = authmethod.request(userobj)
        if not cont:
            break
    return userobj


def setup_from_session():
    userobj = None
    if "user.itemid" in session:
        itemid = session["user.itemid"]
        trusted = session["user.trusted"]
        auth_method = session["user.auth_method"]
        auth_attribs = session["user.auth_attribs"]
        session_token = session["user.session_token"]
        logging.debug(f"got from session: {itemid!r} {trusted!r} {auth_method!r} {auth_attribs!r}")
        logging.debug(f"current auth methods: {app.cfg.auth_methods!r}")
        if auth_method and auth_method in app.cfg.auth_methods:
            userobj = user.User(itemid, auth_method=auth_method, auth_attribs=auth_attribs, trusted=trusted)
            if not userobj.validate_session(session_token):
                logging.debug("session token doesn't validate")
                # Destroy current session since it's no longer valid.
                userobj.logout_session(False)
                # We didn't find user in session data.
                userobj = None
    logging.debug(f"session started for user {userobj!r}")
    return userobj
