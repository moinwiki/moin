# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2005-2013 MoinMoin:ThomasWaldmann
# Copyright: 2008      MoinMoin:JohannesBerg
# Copyright: 2010      MoinMoin:DiogenesAugusto
# Copyright: 2011      MoinMoin:AkashSinha
# Copyright: 2023      MoinMoin project
# Copyright: 2024      MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Configuration defaults class
"""


import re
import os

from babel import Locale, parse_locale

from moin.i18n import _, L_, N_
from moin import error
from moin.constants.rights import ACL_RIGHTS_CONTENTS, ACL_RIGHTS_FUNCTIONS
from moin.constants.keys import *
from moin.items.content import content_registry_enable, content_registry_disable
from moin import datastructures
from moin.auth import MoinAuth
from moin.utils import plugins
from moin.security import AccessControlList, DefaultSecurityPolicy

from moin import log

logging = log.getLogger(__name__)


class CacheClass:
    """just a container for stuff we cache"""

    pass


class ConfigFunctionality:
    """Configuration base class with config class behaviour.

    This class contains the functionality for the DefaultConfig
    class for the benefit of the WikiConfig macro.
    """

    # attributes of this class that should not be shown
    # in the WikiConfig() macro.
    siteid = None
    cache = None
    mail_enabled = None
    auth_can_logout = None
    auth_have_login = None
    auth_login_inputs = None
    _site_plugin_lists = None

    def __init__(self):
        """Init Config instance"""
        self.cache = CacheClass()

        if self.config_check_enabled:
            self._config_check()

        # define directories
        data_dir = os.path.normpath(self.data_dir)
        self.data_dir = data_dir

        # Try to decode certain names which allow unicode
        self._decode()

        # After that, pre-compile some regexes
        self.cache.item_dict_regex = re.compile(self.item_dict_regex, re.UNICODE)
        self.cache.item_group_regex = re.compile(self.item_group_regex, re.UNICODE)

        # the ..._regexact versions only match if nothing is left (exact match)
        self.cache.item_dict_regexact = re.compile(f"^{self.item_dict_regex}$", re.UNICODE)
        self.cache.item_group_regexact = re.compile(f"^{self.item_group_regex}$", re.UNICODE)

        # compiled functions ACL
        self.cache.acl_functions = AccessControlList([self.acl_functions], valid=self.acl_rights_functions)

        plugins._loadPluginModule(self)

        if self.user_defaults[TIMEZONE] is None:
            self.user_defaults[TIMEZONE] = self.timezone_default
        if self.user_defaults[THEME_NAME] is None:
            self.user_defaults[THEME_NAME] = self.theme_default
        # Note: do not assign user_defaults['locale'] = locale_default
        # to give browser language detection a chance.
        try:
            self.language_default = parse_locale(self.locale_default)[0]
            self.content_dir = Locale(self.language_default).text_direction
        except Exception:  # noqa
            raise error.ConfigurationError("Invalid locale_default value (give something like 'en_US').")

        # post process
        self.auth_can_logout = []
        self.auth_login_inputs = []
        found_names = []
        for auth in self.auth:
            if not auth.name:
                raise error.ConfigurationError("Auth methods must have a name.")
            if auth.name in found_names:
                raise error.ConfigurationError("Auth method names must be unique.")
            found_names.append(auth.name)
            if auth.logout_possible and auth.name:
                self.auth_can_logout.append(auth.name)
            for input in auth.login_inputs:
                if input not in self.auth_login_inputs:
                    self.auth_login_inputs.append(input)
        self.auth_have_login = len(self.auth_login_inputs) > 0
        self.auth_methods = found_names

        # internal dict for plugin 'modules' lists
        self._site_plugin_lists = {}

        # check if mail is possible and set flag:
        self.mail_enabled = (self.mail_smarthost is not None or self.mail_sendmail is not None) and self.mail_from
        self.mail_enabled = self.mail_enabled and True or False

        if self.namespace_mapping is None:
            raise error.ConfigurationError(
                "No storage configuration specified! You need to define a namespace_mapping."
            )

        if self.backend_mapping is None:
            raise error.ConfigurationError("No storage configuration specified! You need to define a backend_mapping.")

        if self.acl_mapping is None:
            raise error.ConfigurationError("No acl configuration specified! You need to define a acl_mapping.")

        if self.secrets is None:  # admin did not setup a real secret
            raise error.ConfigurationError(
                "No secret configured! You need to set secrets = 'somelongsecretstring' in your wiki config."
            )

        if self.interwikiname is None:  # admin did not setup a real interwikiname
            raise error.ConfigurationError(
                "No interwikiname configured! "
                "You need to set interwikiname = 'YourUniqueStableInterwikiName' in your wiki config."
            )

        secret_key_names = ["security/ticket"]

        secret_min_length = 10
        if isinstance(self.secrets, str):
            if len(self.secrets) < secret_min_length:
                raise error.ConfigurationError(
                    "The secrets = '...' wiki config setting is a way too short string "
                    "(minimum length is {} chars)!".format(secret_min_length)
                )
            # for lazy people: set all required secrets to same value
            secrets = {}
            for key in secret_key_names:
                secrets[key] = self.secrets
            self.secrets = secrets

        # we check if we have all secrets we need and that they have minimum length
        for secret_key_name in secret_key_names:
            try:
                secret = self.secrets[secret_key_name]
                if len(secret) < secret_min_length:
                    raise ValueError
            except (KeyError, ValueError):
                raise error.ConfigurationError(
                    "You must set a (at least {} chars long) secret string for secrets['{}']!".format(
                        secret_min_length, secret_key_name
                    )
                )

        from passlib.context import CryptContext

        try:
            self.cache.pwd_context = CryptContext(**self.passlib_crypt_context)
        except ValueError as err:
            raise error.ConfigurationError(f"passlib_crypt_context configuration is invalid [{err}].")

        if len(self.contenttype_enabled):
            content_registry_enable(self.contenttype_enabled)
        elif len(self.contenttype_disabled):
            content_registry_disable(self.contenttype_disabled)

    def _config_check(self):
        """Check namespace and warn about unknown names

        Warn about names which are not used by DefaultConfig, except
        modules, classes, _private or __magic__ names.

        This check is disabled by default, when enabled, it will show an
        error message with unknown names.
        """
        unknown = [
            f'"{name}"'
            for name in dir(self)
            if not name.startswith("_")
            and name not in DefaultConfig.__dict__
            and not isinstance(getattr(self, name), (type(re), type(DefaultConfig)))
        ]
        if unknown:
            msg = """
Unknown configuration options: {}.

For more information, see configuration docs. Please check your
configuration for typos before requesting support or reporting a bug.
""".format(
                ", ".join(unknown)
            )
            raise error.ConfigurationError(msg)

    def _decode(self):
        """Try to decode certain names, ignore unicode values

        Try to decode str using utf-8. If the decode fail, raise FatalError.

        Certain config variables should contain unicode values, and
        should be defined with 'text' syntax. Python will decode these if
        the file has a 'coding' line.
        """
        charset = "utf-8"
        message = """
"{name}" configuration variable is a string, but should be
unicode. Use {name} = "value" syntax for unicode variables.

Also check your "-*- coding -*-" line at the top of your configuration
file. It should match the actual charset of the configuration file.
"""

        decode_names = (
            "sitename",
            "interwikiname",
            "user_homewiki",
            "interwiki_preferred",
            "item_license",
            "mail_from",
            "item_dict_regex",
            "item_group_regex",
            "acl_functions",
            "supplementation_item_names",
            "html_pagetitle",
            "theme_default",
            "timezone_default",
            "locale_default",
        )

        for name in decode_names:
            attr = getattr(self, name, None)
            if attr is not None:
                # Try to decode strings
                if isinstance(attr, bytes):
                    try:
                        setattr(self, name, str(attr, charset))
                    except UnicodeError:
                        raise error.ConfigurationError(message.format(name=name))
                # Look into lists and try to decode strings inside them
                elif isinstance(attr, list):
                    for i in range(len(attr)):
                        item = attr[i]
                        if isinstance(item, bytes):
                            try:
                                attr[i] = str(item, charset)
                            except UnicodeError:
                                raise error.ConfigurationError(message.format(name=name))

    def __getitem__(self, item):
        """Make it possible to access a config object like a dict"""
        return getattr(self, item)


class DefaultConfig(ConfigFunctionality):
    """Configuration base class with default config values
    (added below)
    """

    # Do not add anything into this class. Functionality must
    # be added above to avoid having the methods show up in
    # the WikiConfig macro. Settings must be added below to
    # the options dictionary.


def _default_password_checker(cfg, username, password, min_length=8, min_different=5):
    """Check if a password is secure enough.
    We use a built-in check to get rid of the worst passwords.

    We do NOT use cracklib / python-crack here any more because it is
    not thread-safe (we experienced segmentation faults when using it).

    If you don't want to check passwords, use password_checker = None.

    :returns: None if there is no problem with the password,
             some unicode object with an error msg, if the password is problematic.
    """
    # in any case, do a very simple built-in check to avoid the worst passwords
    if len(password) < min_length:
        return _(
            "For a password a minimum length of {min_length} characters is required.".format(min_length=min_length)
        )
    if len(set(password)) < min_different:
        return _(
            "For a password a minimum of {min_different:d} different characters is required.".format(
                min_different=min_different
            )
        )

    username_lower = username.lower()
    password_lower = password.lower()
    if (
        username in password
        or password in username
        or username_lower in password_lower
        or password_lower in username_lower
    ):
        return _("Password is too easy to guess (password contains name or name contains password).")

    keyboards = (
        r"`1234567890-=qwertyuiop[]\asdfghjkl;'zxcvbnm,./",  # US kbd
        r"^1234567890ß´qwertzuiopü+asdfghjklöä#yxcvbnm,.-",  # german kbd
    )  # TODO add more keyboards!
    for kbd in keyboards:
        rev_kbd = kbd[::-1]
        if password in kbd or password in rev_kbd or password_lower in kbd or password_lower in rev_kbd:
            return _("Password is too easy to guess (keyboard sequence).")
    return None


class DefaultExpression:
    def __init__(self, exprstr):
        self.text = exprstr
        self.value = eval(exprstr)


#
# Options that are not prefixed automatically with their
# group name, see below (at the options dict) for more
# information on the layout of this structure.
#
options_no_group_name = {
    # ==========================================================================
    "datastructures": (
        "Datastruct",
        None,
        (
            # ('dicts', lambda cfg: datastructures.ConfigDicts({}),
            (
                "dicts",
                lambda cfg: datastructures.WikiDicts(),
                "function f(cfg) that returns a backend which is used to access dicts definitions.",
            ),
            # ('groups', lambda cfg: datastructures.ConfigGroups({}),
            (
                "groups",
                lambda cfg: datastructures.WikiGroups(),
                "function f(cfg) that returns a backend which is used to access groups definitions.",
            ),
        ),
    ),
    # ==========================================================================
    "auth": (
        "Authentication / Authorization / Security",
        None,
        (
            ("auth", DefaultExpression("[MoinAuth()]"), "list of auth objects, to be called in order as specified"),
            (
                "secrets",
                None,
                """Either a long shared secret string used for multiple purposes or a dict {"purpose": "longsecretstring", ...} for setting up different shared secrets for different purposes.""",
            ),
            (
                "SecurityPolicy",
                DefaultSecurityPolicy,
                "Class object hook for implementing security restrictions or relaxations",
            ),
            ("endpoints_excluded", [], "Exclude unwanted endpoints (list of strings)"),
            (
                "password_checker",
                DefaultExpression("_default_password_checker"),
                'does simple checks whether a password is acceptable (you can switch this off by using "None" or enhance it by using a custom checker)',
            ),
            (
                "passlib_crypt_context",
                dict(
                    # schemes we want to support (or deprecated schemes for which we still have
                    # hashes in our storage).
                    # note about bcrypt: it needs additional code (that is not pure python and
                    # thus either needs compiling or installing platform-specific binaries)
                    schemes=["sha512_crypt"],
                    # default scheme for creating new pw hashes (if not given, passlib uses first from schemes)
                    # default="sha512_crypt",
                    # deprecated schemes get auto-upgraded to the default scheme at login
                    # time or when setting a password (including doing a moin account pwreset).
                    # deprecated=["auto"],
                    # vary rounds parameter randomly when creating new hashes...
                    # all__vary_rounds=0.1,
                ),
                "passlib CryptContext arguments, see passlib docs",
            ),
            (
                "allow_style_attributes",
                False,
                "trust editors to not abuse style attribute security holes within HTML (CKEditor) or Markdown items",
            ),
        ),
    ),
    # ==========================================================================
    "style": (
        "Style / Theme / UI",
        "These settings control how the wiki user interface will look like.",
        (
            (
                "sitename",
                "Untitled Wiki",
                "Short description of your wiki site, displayed below the logo on each page, and used in RSS documents as the channel title [Unicode]",
            ),
            (
                "interwikiname",
                None,
                "unique, stable and required InterWiki name (prefix, moniker) of the site [Unicode]",
            ),
            (
                "html_pagetitle",
                None,
                "Allows you to set a specific HTML page title (if None, it defaults to the value of 'sitename') [Unicode]",
            ),
            (
                "navi_bar",
                [
                    # cls, endpoint, args, link_text, title
                    ("wikilink", "frontend.show_root", dict(), L_("Home"), L_("Home Page")),
                    ("wikilink", "frontend.global_history", dict(), L_("History"), L_("Global History")),
                    ("wikilink", "frontend.index", dict(), L_("Index"), L_("Global Index")),
                    ("wikilink", "frontend.global_tags", dict(), L_("Tags"), L_("Global Tags Index")),
                    ("wikilink", "admin.index_user", dict(), L_("User"), L_("User")),
                    ("wikilink", "admin.index", dict(), L_("Admin"), L_("Administration & Docs")),
                    # TODO: tickets are broken
                    # ('wikilink', 'frontend.tickets', dict(), L_('Tickets'), L_('List of Tickets')),
                ],
                "Data to create the navi_bar from. Users can add more items in their quick links in user preferences. You need to configure a list of tuples (css_class, endpoint, args, label, title). Use L_() for translating. [list of tuples]",
            ),
            ("expanded_quicklinks_size", 8, "Number of quicklinks to show as expanded in navi bar"),
            ("theme_default", "topside", "Default theme."),
            (
                "serve_files",
                {},
                """
         Dictionary of name: filesystem_path for static file resources to serve
         from the filesystem as url .../+serve/<name>/...
         """,
            ),
            (
                "supplementation_item_names",
                [_("Discussion")],
                "List of names of the supplementation (sub)items [Unicode]",
            ),
            ("interwiki_preferred", [], "In dialogues, show those wikis at the top of the list [list of Unicode]."),
            ("sistersites", [], "list of tuples: (<WikiName>, <sisterpagelist_fetch_url>)"),
            ("trail_size", 5, "Number of items in the trail of recently visited items"),
            (
                "item_views",
                [
                    # (endpointname, label, title, check_item_exists
                    ("frontend.show_item", L_("Show"), L_("Show"), False),
                    ("frontend.modify_item", L_("Modify"), L_("Edit or Upload"), False),
                    ("frontend.history", L_("History"), L_("Revision History"), True),
                    ("frontend.download_item", L_("Download"), L_("Download"), True),
                    ("frontend.delete_item", L_("Delete"), L_("Delete this item"), True),
                    ("frontend.quicklink_item", None, L_("Create or remove a navigation link to this item"), False),
                    ("frontend.subscribe_item", None, L_("Switch notifications about item changes on or off"), False),
                    ("frontend.index", L_("Subitems"), L_("Subitems Index"), False),
                    ("special.supplementation", None, None, False),
                    ("frontend.rename_item", L_("Rename"), L_("Rename this item"), True),
                    ("frontend.highlight_item", L_("Highlight"), L_("Show with Syntax-Highlighting"), True),
                    ("frontend.show_item_meta", L_("Meta"), L_("Display Metadata"), True),
                    ("frontend.sitemap", L_("Site Map"), L_("Local Site Map of this item"), True),
                    ("frontend.similar_names", L_("Similar"), L_("Items with similar names"), False),
                    ("frontend.convert_item", L_("Convert"), L_("Convert this item"), True),
                    ("frontend.destroy_item", L_("Destroy"), L_("Completely destroy this item"), True),
                    ("special.comments", L_("Comments"), L_("Hide comments"), True),
                    ("special.transclusions", L_("Transclusions"), L_("Show transclusions"), True),
                ],
                "list of edit bar entries (list of tuples (endpoint, label, title, exists))",
            ),
            ("show_hosts", True, "if True, show host names and IPs. Set to False to hide them."),
            ("show_interwiki", False, "if True, let the theme display your interwiki name"),
            ("show_names", True, "if True, show user names in the revision history. Set to False to hide them."),
            ("show_section_numbers", False, "show section numbers in headings by default"),
            ("show_rename_redirect", False, "if True, offer creation of redirect pages when renaming wiki pages"),
            ("template_dirs", [], "list of directories with templates that will override theme and base templates."),
        ),
    ),
    # ==========================================================================
    "editor": (
        "Editor",
        None,
        (
            (
                "edit_locking_policy",
                "lock",
                "Editor locking policy: None or 'lock'",
            ),  # 'warn' as in 1.9.x is not supported
            ("edit_lock_time", 10, "Time, in minutes, to hold or renew edit lock at start of edit or preview"),
            # ('item_license', '', 'not used: maybe page_license_enabled from 1.9.x; if set, show the license item within the editor. [Unicode]'),
            # ('edit_ticketing', True, 'not used: maybe a remnant of https://moinmo.in/TicketSystem'),
        ),
    ),
    # ==========================================================================
    "paging": (
        "Paging",
        None,
        (("results_per_page", 50, "Number of results to be shown on a single page in pagination"),),
    ),
    # ==========================================================================
    "data": (
        "Data Storage",
        None,
        (
            ("data_dir", "./data/", "Path to the data directory."),
            ("plugin_dirs", [], "Plugin directories."),
            ("interwiki_map", {}, "Dictionary of wiki_name -> wiki_url"),
            (
                "namespace_mapping",
                None,
                "A list of tuples, each tuple containing: Namespace identifier, backend name. "
                + "E.g.: [('', 'default')), ].",
            ),
            (
                "backend_mapping",
                None,
                "A dictionary that maps backend names to backends. " + "E.g.: {'default': Backend(), }.",
            ),
            (
                "acl_mapping",
                None,
                "This needs to point to a list of tuples, each tuple containing: name prefix, acl protection to be applied to matching items. "
                + "E.g.: [('', dict(default='All:read,write,create,admin')), ].",
            ),
            ("mimetypes_to_index_as_empty", [], "List of mimetypes which are indexed as though they were empty."),
        ),
    ),
    # ==========================================================================
    "items": (
        "Special Item Names",
        None,
        (
            (
                "default_root",
                "Home",
                "Default root, use this value in case no match is found in root_mapping. [Unicode]",
            ),
            ("root_mapping", {}, "mapping of namespaces to item_roots."),
            # the following regexes should match the complete name when used in free text
            # the group 'all' shall match all, while the group 'key' shall match the key only
            # e.g. FooGroup -> group 'all' ==  FooGroup, group 'key' == Foo
            # moin's code will add ^ / $ at beginning / end when needed
            (
                "item_dict_regex",
                r"(?P<all>(?P<key>\S+)Dict)",
                "Item names exactly matching this regex are regarded as items containing variable dictionary definitions [Unicode]",
            ),
            (
                "item_group_regex",
                r"(?P<all>(?P<key>\S+)Group)",
                "Item names exactly matching this regex are regarded as items containing group definitions [Unicode]",
            ),
        ),
    ),
    # ==========================================================================
    "user": (
        "User Preferences",
        None,
        (
            (
                "user_defaults",
                {
                    NAME: [],
                    DISPLAY_NAME: None,
                    EMAIL: None,
                    CSS_URL: None,
                    ISO_8601: False,
                    MAILTO_AUTHOR: False,
                    EDIT_ON_DOUBLECLICK: True,
                    SCROLL_PAGE_AFTER_EDIT: True,
                    SHOW_COMMENTS: False,
                    WANT_TRIVIAL: False,
                    ENC_PASSWORD: "",  # empty value == invalid hash
                    RECOVERPASS_KEY: "",  # empty value == invalid key
                    SESSION_KEY: "",  # empty value == invalid key
                    DISABLED: False,
                    BOOKMARKS: {},
                    QUICKLINKS: [],
                    SUBSCRIPTIONS: [],
                    EMAIL_SUBSCRIBED_EVENTS: [
                        # XXX PageChangedEvent.__name__
                        # XXX PageRenamedEvent.__name__
                        # XXX PageDeletedEvent.__name__
                        # XXX PageCopiedEvent.__name__
                        # XXX PageRevertedEvent.__name__
                    ],
                    THEME_NAME: None,  # None -> use cfg.theme_default
                    EDIT_ROWS: 0,
                    RESULTS_PER_PAGE: 50,
                    LOCALE: None,  # None -> do browser language detection, otherwise just use this locale
                    TIMEZONE: None,  # None -> use cfg.timezone_default
                    EMAIL_UNVALIDATED: None,
                },
                "Default attributes of the user object",
            ),
        ),
    ),
    # ==========================================================================
    "various": (
        "Various",
        None,
        (
            # ('bang_meta', True, 'if True, enable {{{#!NoWikiName}}} markup'),
            ("config_check_enabled", False, "if True, check configuration for unknown settings."),
            ("timezone_default", "UTC", "Default time zone."),
            ("locale_default", "en_US", "Default locale for user interface and content."),
            # ('log_remote_addr', True, "if True, log the remote IP address (and maybe hostname)."),
            (
                "log_reverse_dns_lookups",
                True,
                "if True, do a reverse DNS lookup on page SAVE. If your DNS is broken, set this to False to speed up SAVE.",
            ),
            # some dangerous mimetypes (we don't use "content-disposition: inline" for them when a user
            # downloads such data, because the browser might execute e.g. Javascript contained
            # in the HTML and steal your moin session cookie or do other nasty stuff)
            (
                "mimetypes_xss_protect",
                ["text/html", "application/x-shockwave-flash", "application/xhtml+xml"],
                '"content-disposition: inline" is not used for downloads of such data',
            ),
            # ('refresh', None, "refresh = (minimum_delay_s, targets_allowed) enables use of '#refresh 5 PageName' processing instruction, targets_allowed must be either 'internal' or 'external'"),
            ("siteid", "MoinMoin", None),  # XXX just default to some existing module name to
            # make plugin loader etc. work for now
            ("contenttype_disabled", [], "List of disabled content types. Ignored if contenttype_enabled is set."),
            (
                "contenttype_enabled",
                [],
                "List of available content types for new items. Default: [] (all types enabled).",
            ),
        ),
    ),
}

#
# The 'options' dict carries default MoinMoin options. The dict is a
# group name to tuple mapping.
# Each group tuple consists of the following items:
#   group section heading, group help text, option list
#
# where each 'option list' is a tuple or list of option tuples
#
# each option tuple consists of
#   option name, default value, help text
#
# Unlike the options_no_group_name dict, option names in this dict
# are automatically prefixed with "group name '_'" (i.e. the name of
# the group they are in and an underscore), e.g. the 'hierarchic'
# below creates an option called "acl_hierarchic".
#
# If you need to add a complex default expression that results in an
# object and should not be shown in the __repr__ form in WikiConfigHelp(),
# you can use the DefaultExpression class, see 'auth' above for example.
#
#
options = {
    "acl": (
        "Access Control Lists",
        "ACLs control who may do what.",
        (
            ("functions", "", "Access Control List for functions."),
            ("rights_contents", ACL_RIGHTS_CONTENTS, "Valid tokens for right sides of content ACL entries."),
            ("rights_functions", ACL_RIGHTS_FUNCTIONS, "Valid tokens for right sides of function ACL entries."),
        ),
    ),
    "ns": (
        "Storage Namespaces",
        "Storage namespaces can be defined for all sorts of data. "
        "All items sharing a common namespace as prefix are then stored within the same backend. "
        "The common prefix for all data is ''.",
        (
            (
                "content",
                "/",
                "All content is by default stored below /, hence the prefix is ''.",
            ),  # Not really necessary. Just for completeness.
            (
                "user_profile",
                "userprofiles/",
                "User profiles (i.e. user data, not their homepage) are stored in this namespace.",
            ),
            ("user_homepage", "users/", "All user homepages are stored in this namespace."),
        ),
    ),
    "user": (
        "User",
        None,
        (
            ("email_unique", True, "if True, check email addresses for uniqueness and don't accept duplicates."),
            (
                "email_verification",
                False,
                "if True, require a new user to verify his or her email address before the first login.",
            ),
            (
                "homewiki",
                "Self",
                "interwiki name of the wiki where the user home pages are located [Unicode] - useful if you have ''many'' users. You could even link to nonwiki \"user pages\" if the wiki username is in the target URL.",
            ),
            ("use_gravatar", False, "if True, gravatar.com will be used to find User's avatar"),
        ),
    ),
    "mail": (
        "Mail",
        "These settings control outgoing and incoming email from and to the wiki.",
        (
            ("from", None, "Used as From: address for generated mail. [Unicode]"),
            ("username", None, "Username for SMTP server authentication (None = don't use auth)."),
            ("password", None, "Password for SMTP server authentication (None = don't use auth)."),
            ("smarthost", None, "Address of SMTP server to use for sending mail (None = don't use SMTP server)."),
            ("sendmail", None, "sendmail command to use for sending mail (None = don't use sendmail)"),
        ),
    ),
    "registration": (
        "Registration",
        "These settings control registration options",
        (
            ("only_by_superuser", False, "True is recommended value for public wikis on the internet."),
            (
                "hint",
                _("To request an account, see bottom of Home page."),
                "message on login page when only_by_superuser is True",
            ),
        ),
    ),
}


def _add_options_to_defconfig(opts, addgroup=True):
    for groupname in opts:
        group_short, group_doc, group_opts = opts[groupname]
        for name, default, doc in group_opts:
            if addgroup:
                name = groupname + "_" + name
            if isinstance(default, DefaultExpression):
                default = default.value
            setattr(DefaultConfig, name, default)


_add_options_to_defconfig(options)
_add_options_to_defconfig(options_no_group_name, False)
