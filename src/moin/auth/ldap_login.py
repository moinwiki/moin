# Copyright: 2006-2008 MoinMoin:ThomasWaldmann
# Copyright: 2006 Nick Phillips
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - LDAP / Active Directory authentication

    This code only creates a user object, the session will be established by
    moin automatically.

    python-ldap needs to be at least 2.0.0pre06 (available since mid 2002) for
    ldaps support - some older debian installations (woody and older?) require
    libldap2-tls and python2.x-ldap-tls, otherwise you get ldap.SERVER_DOWN:
    "Can't contact LDAP server" - more recent debian installations have tls
    support in libldap2 (see dependency on gnutls) and also in python-ldap.

    TODO: allow more configuration (display name, ...) by using callables as parameters
"""


from moin import user
from moin.i18n import _
from moin.auth import BaseAuth, CancelLogin, ContinueLogin

from moin import log

logging = log.getLogger(__name__)

try:
    import ldap
except ImportError as err:
    logging.error(f"You need to have python-ldap installed ({err!s}).")
    raise


class LDAPAuth(BaseAuth):
    """get authentication data from form, authenticate against LDAP (or Active
    Directory), fetch some user infos from LDAP and create a user object
    for that user. The session is kept by moin automatically.
    """

    login_inputs = ["username", "password"]
    logout_possible = True
    name = "ldap"

    def __init__(
        self,
        trusted=True,
        server_uri="ldap://localhost",  # ldap / active directory server URI
        # use ldaps://server:636 url for ldaps,
        # use  ldap://server for ldap without tls (and set start_tls to 0),
        # use  ldap://server for ldap with tls (and set start_tls to 1 or 2).
        bind_dn="",  # We can either use some fixed user and password for binding to LDAP.
        # Be careful if you need a % char in those strings - as they are used as
        # a format string, you have to write %% to get a single % in the end.
        # bind_dn = 'binduser@example.org' # (AD)
        # bind_dn = 'cn=admin,dc=example,dc=org' # (OpenLDAP)
        # bind_pw = 'secret'
        # or we can use the username and password we got from the user:
        # bind_dn = '%(username)s@example.org' # DN we use for first bind (AD)
        # bind_pw = '%(password)s' # password we use for first bind
        # or we can bind anonymously (if that is supported by your directory).
        # In any case, bind_dn and bind_pw must be defined.
        bind_pw="",
        base_dn="",  # base DN we use for searching
        # base_dn = 'ou=SOMEUNIT,dc=example,dc=org'
        scope=ldap.SCOPE_SUBTREE,  # scope of the search we do (2 == ldap.SCOPE_SUBTREE)
        referrals=0,  # LDAP REFERRALS (0 needed for AD)
        search_filter="(uid=%(username)s)",  # ldap filter used for searching:
        # search_filter = '(sAMAccountName=%(username)s)' # (AD)
        # search_filter = '(uid=%(username)s)' # (OpenLDAP)
        # you can also do more complex filtering like:
        # "(&(cn=%(username)s)(memberOf=CN=WikiUsers,OU=Groups,DC=example,DC=org))"
        # some attribute names we use to extract information from LDAP:
        givenname_attribute=None,  # ('givenName') ldap attribute we get the first name from
        surname_attribute=None,  # ('sn') ldap attribute we get the family name from
        displayname_attribute=None,  # ('displayName') ldap attribute we get the display_name from
        email_attribute=None,  # ('mail') ldap attribute we get the email address from
        email_callback=None,  # called to make up email address
        name_callback=None,  # called to use a Wiki name different from the login name
        coding="utf-8",  # coding used for ldap queries and result values
        timeout=10,  # how long we wait for the ldap server [s]
        start_tls=0,  # 0 = No, 1 = Try, 2 = Required
        tls_cacertdir=None,
        tls_cacertfile=None,
        tls_certfile=None,
        tls_keyfile=None,
        tls_require_cert=0,  # 0 == ldap.OPT_X_TLS_NEVER (needed for self-signed certs)
        bind_once=False,  # set to True to only do one bind - useful if configured to bind as the user on first attempt
        autocreate=False,  # set to True if you want to autocreate user profiles
        name="ldap",  # use e.g. 'ldap_pdc' and 'ldap_bdc' (or 'ldap1' and 'ldap2') if you auth against 2 ldap servers
        report_invalid_credentials=True,  # whether to emit "invalid username or password" msg at login time or not
        **kw,
    ):
        super().__init__(**kw)
        self.server_uri = server_uri
        self.bind_dn = bind_dn
        self.bind_pw = bind_pw
        self.base_dn = base_dn
        self.scope = scope
        self.referrals = referrals
        self.search_filter = search_filter

        self.givenname_attribute = givenname_attribute
        self.surname_attribute = surname_attribute
        self.displayname_attribute = displayname_attribute
        self.email_attribute = email_attribute
        self.email_callback = email_callback
        self.name_callback = name_callback

        self.coding = coding
        self.timeout = timeout

        self.start_tls = start_tls
        self.tls_cacertdir = tls_cacertdir
        self.tls_cacertfile = tls_cacertfile
        self.tls_certfile = tls_certfile
        self.tls_keyfile = tls_keyfile
        self.tls_require_cert = tls_require_cert

        self.bind_once = bind_once
        self.autocreate = autocreate
        self.name = name

        self.report_invalid_credentials = report_invalid_credentials

    def login(self, user_obj, **kw):
        username = kw.get("username")
        password = kw.get("password")

        # we require non-empty password as ldap bind does a anon (not password
        # protected) bind if the password is empty and SUCCEEDS!
        if not password:
            return ContinueLogin(user_obj, _("Missing password. Please enter user name and password."))

        try:
            try:
                u = None
                dn = None
                server = self.server_uri
                coding = self.coding
                logging.debug("Setting misc. ldap options...")
                ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)  # ldap v2 is outdated
                ldap.set_option(ldap.OPT_REFERRALS, self.referrals)
                ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, self.timeout)

                if hasattr(ldap, "TLS_AVAIL") and ldap.TLS_AVAIL:
                    for option, value in (
                        (ldap.OPT_X_TLS_CACERTDIR, self.tls_cacertdir),
                        (ldap.OPT_X_TLS_CACERTFILE, self.tls_cacertfile),
                        (ldap.OPT_X_TLS_CERTFILE, self.tls_certfile),
                        (ldap.OPT_X_TLS_KEYFILE, self.tls_keyfile),
                        (ldap.OPT_X_TLS_REQUIRE_CERT, self.tls_require_cert),
                        (ldap.OPT_X_TLS, self.start_tls),
                        # (ldap.OPT_X_TLS_ALLOW, 1),
                    ):
                        if value is not None:
                            ldap.set_option(option, value)

                logging.debug(f"Trying to initialize {server!r}.")
                conn = ldap.initialize(server)
                logging.debug(f"Connected to LDAP server {server!r}.")

                if self.start_tls and server.startswith("ldap:"):
                    logging.debug(f"Trying to start TLS to {server!r}.")
                    try:
                        conn.start_tls_s()
                        logging.debug(f"Using TLS to {server!r}.")
                    except (ldap.SERVER_DOWN, ldap.CONNECT_ERROR) as err:
                        logging.warning(f"Couldn't establish TLS to {server!r} (err: {err!s}).")
                        raise

                # you can use %(username)s and %(password)s here to get the stuff entered in the form:
                binddn = self.bind_dn % locals()
                bindpw = self.bind_pw % locals()
                conn.simple_bind_s(binddn, bindpw)
                logging.debug(f"Bound with binddn {binddn!r}")

                # you can use %(username)s here to get the stuff entered in the form:
                filterstr = self.search_filter % locals()
                logging.debug(f"Searching {filterstr!r}")
                attrs = [
                    getattr(self, attr)
                    for attr in ["email_attribute", "displayname_attribute", "surname_attribute", "givenname_attribute"]
                    if getattr(self, attr) is not None
                ]
                lusers = conn.search_st(self.base_dn, self.scope, filterstr, attrlist=attrs, timeout=self.timeout)
                # we remove entries with dn == None to get the real result list:
                lusers = [(_dn, _ldap_dict) for _dn, _ldap_dict in lusers if _dn is not None]
                for _dn, _ldap_dict in lusers:
                    logging.debug(f"dn:{_dn!r}")
                    for key, val in _ldap_dict.items():
                        logging.debug(f"    {key!r}: {val!r}")

                result_length = len(lusers)
                if result_length != 1:
                    if result_length > 1:
                        logging.warning(f"Search found more than one ({result_length}) matches for {filterstr!r}.")
                    if result_length == 0:
                        logging.debug(f"Search found no matches for {filterstr!r}.")
                    if self.report_invalid_credentials:
                        return ContinueLogin(user_obj, _("Invalid username or password."))
                    else:
                        return ContinueLogin(user_obj)

                dn, ldap_dict = lusers[0]
                if not self.bind_once:
                    logging.debug(f"DN found is {dn!r}, trying to bind with pw")
                    conn.simple_bind_s(dn, password)
                    logging.debug(f"Bound with dn {dn!r} (username: {username!r})")

                if self.email_callback is None:
                    if self.email_attribute:
                        email = ldap_dict.get(self.email_attribute, [""])[0]
                    else:
                        email = None
                else:
                    email = self.email_callback(ldap_dict)

                display_name = ""
                try:
                    display_name = ldap_dict[self.displayname_attribute][0]
                except (KeyError, IndexError):
                    pass
                if not display_name:
                    sn = ldap_dict.get(self.surname_attribute, [""])[0]
                    gn = ldap_dict.get(self.givenname_attribute, [""])[0]
                    if sn and gn:
                        display_name = f"{sn}, {gn}"
                    elif sn:
                        display_name = sn

                if self.name_callback:
                    username = self.name_callback(ldap_dict)

                if email:
                    u = user.User(
                        auth_username=username,
                        auth_method=self.name,
                        auth_attribs=("name", "password", "email", "mailto_author"),
                        trusted=self.trusted,
                    )
                    u.email = email
                else:
                    u = user.User(
                        auth_username=username,
                        auth_method=self.name,
                        auth_attribs=("name", "password", "mailto_author"),
                        trusted=self.trusted,
                    )
                u.name = username
                u.display_name = display_name
                logging.debug(
                    "creating user object with name {!r} email {!r} display name {!r}".format(
                        username, email, display_name
                    )
                )

            except ldap.INVALID_CREDENTIALS:
                logging.debug(f"invalid credentials (wrong password?) for dn {dn!r} (username: {username!r})")
                return CancelLogin(_("Invalid username or password."))

            if u and self.autocreate:
                logging.debug(f"calling create_or_update to autocreate user {u.name!r}")
                u.create_or_update(True)
            return ContinueLogin(u)

        except ldap.SERVER_DOWN as err:
            # looks like this LDAP server isn't working, so we just try the next
            # authenticator object in cfg.auth list (there could be some second
            # ldap authenticator that queries a backup server or any other auth
            # method).
            logging.error(f"LDAP server {server} failed ({err!s}). Trying to authenticate with next auth list entry.")
            return ContinueLogin(user_obj, _("LDAP server {server} failed.").format(server=server))

        except:  # noqa
            logging.exception("caught an exception, traceback follows...")
            return ContinueLogin(user_obj)
