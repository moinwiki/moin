# -*- coding: utf-8 -*-
# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2005-2013 MoinMoin:ThomasWaldmann
# Copyright: 2008      MoinMoin:JohannesBerg
# Copyright: 2010      MoinMoin:DiogenesAugusto
# Copyright: 2011      MoinMoin:AkashSinha
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Configuration defaults class
"""


import re
import os

from babel import parse_locale

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.i18n import _, L_, N_
from MoinMoin import error
from MoinMoin.constants.rights import ACL_RIGHTS_CONTENTS, ACL_RIGHTS_FUNCTIONS
from MoinMoin import datastruct
from MoinMoin.auth import MoinAuth
from MoinMoin.util import plugins
from MoinMoin.security import AccessControlList, DefaultSecurityPolicy


class CacheClass(object):
    """ just a container for stuff we cache """
    pass


class ConfigFunctionality(object):
    """ Configuration base class with config class behaviour.

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
        """ Init Config instance """
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
        self.cache.item_dict_regexact = re.compile(u'^{0}$'.format(self.item_dict_regex, re.UNICODE))
        self.cache.item_group_regexact = re.compile(u'^{0}$'.format(self.item_group_regex, re.UNICODE))

        # compiled functions ACL
        self.cache.acl_functions = AccessControlList([self.acl_functions], valid=self.acl_rights_functions)

        plugins._loadPluginModule(self)

        if self.user_defaults['timezone'] is None:
            self.user_defaults['timezone'] = self.timezone_default
        if self.user_defaults['theme_name'] is None:
            self.user_defaults['theme_name'] = self.theme_default
        # Note: do not assign user_defaults['locale'] = locale_default
        # to give browser language detection a chance.
        try:
            self.language_default = parse_locale(self.locale_default)[0]
        except ValueError:
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
                if not input in self.auth_login_inputs:
                    self.auth_login_inputs.append(input)
        self.auth_have_login = len(self.auth_login_inputs) > 0
        self.auth_methods = found_names

        # internal dict for plugin `modules' lists
        self._site_plugin_lists = {}

        # check if mail is possible and set flag:
        self.mail_enabled = (self.mail_smarthost is not None or self.mail_sendmail is not None) and self.mail_from
        self.mail_enabled = self.mail_enabled and True or False

        if self.namespace_mapping is None:
            raise error.ConfigurationError(
                "No storage configuration specified! You need to define a namespace_mapping. "
                "For further reference, please see HelpOnStorageConfiguration.")

        if self.backend_mapping is None:
            raise error.ConfigurationError(
                "No storage configuration specified! You need to define a backend_mapping. " +
                "For further reference, please see HelpOnStorageConfiguration.")

        if self.acl_mapping is None:
            raise error.ConfigurationError(
                "No acl configuration specified! You need to define a acl_mapping. "
                "For further reference, please see HelpOnStorageConfiguration.")

        if self.secrets is None:  # admin did not setup a real secret
            raise error.ConfigurationError(
                "No secret configured! You need to set secrets = 'somelongsecretstring' in your wiki config.")

        if self.interwikiname is None:  # admin did not setup a real interwikiname
            raise error.ConfigurationError(
                "No interwikiname configured! "
                "You need to set interwikiname = u'YourUniqueStableInterwikiName' in your wiki config.")

        secret_key_names = ['security/ticket', ]
        if self.textchas:
            secret_key_names.append('security/textcha')

        secret_min_length = 10
        if isinstance(self.secrets, str):
            if len(self.secrets) < secret_min_length:
                raise error.ConfigurationError(
                    "The secrets = '...' wiki config setting is a way too short string "
                    "(minimum length is {0} chars)!".format(secret_min_length))
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
                    "You must set a (at least {0} chars long) secret string for secrets['{1}']!".format(
                    secret_min_length, secret_key_name))

        from passlib.context import CryptContext
        try:
            self.cache.pwd_context = CryptContext(**self.passlib_crypt_context)
        except ValueError as err:
            raise error.ConfigurationError("passlib_crypt_context configuration is invalid [{0}].".format(err))

    def _config_check(self):
        """ Check namespace and warn about unknown names

        Warn about names which are not used by DefaultConfig, except
        modules, classes, _private or __magic__ names.

        This check is disabled by default, when enabled, it will show an
        error message with unknown names.
        """
        unknown = ['"{0}"'.format(name) for name in dir(self)
                  if not name.startswith('_') and
                  name not in DefaultConfig.__dict__ and
                  not isinstance(getattr(self, name), (type(re), type(DefaultConfig)))]
        if unknown:
            msg = """
Unknown configuration options: {0}.

For more information, visit HelpOnConfiguration. Please check your
configuration for typos before requesting support or reporting a bug.
""".format(', '.join(unknown))
            raise error.ConfigurationError(msg)

    def _decode(self):
        """ Try to decode certain names, ignore unicode values

        Try to decode str using utf-8. If the decode fail, raise FatalError.

        Certain config variables should contain unicode values, and
        should be defined with u'text' syntax. Python decode these if
        the file have a 'coding' line.

        This will allow utf-8 users to use simple strings using, without
        using u'string'. Other users will have to use u'string' for
        these names, because we don't know what is the charset of the
        config files.
        """
        charset = 'utf-8'
        message = u"""
"%(name)s" configuration variable is a string, but should be
unicode. Use %(name)s = u"value" syntax for unicode variables.

Also check your "-*- coding -*-" line at the top of your configuration
file. It should match the actual charset of the configuration file.
"""

        decode_names = (
            'sitename', 'interwikiname', 'user_homewiki',
            'interwiki_preferred',
            'item_root', 'item_license', 'mail_from',
            'item_dict_regex', 'item_group_regex',
            'acl_functions', 'supplementation_item_names', 'html_pagetitle',
            'theme_default', 'timezone_default', 'locale_default',
        )

        for name in decode_names:
            attr = getattr(self, name, None)
            if attr is not None:
                # Try to decode strings
                if isinstance(attr, str):
                    try:
                        setattr(self, name, unicode(attr, charset))
                    except UnicodeError:
                        raise error.ConfigurationError(message %
                                                       {'name': name})
                # Look into lists and try to decode strings inside them
                elif isinstance(attr, list):
                    for i in xrange(len(attr)):
                        item = attr[i]
                        if isinstance(item, str):
                            try:
                                attr[i] = unicode(item, charset)
                            except UnicodeError:
                                raise error.ConfigurationError(message %
                                                               {'name': name})

    def __getitem__(self, item):
        """ Make it possible to access a config object like a dict """
        return getattr(self, item)


class DefaultConfig(ConfigFunctionality):
    """ Configuration base class with default config values
        (added below)
    """
    # Do not add anything into this class. Functionality must
    # be added above to avoid having the methods show up in
    # the WikiConfig macro. Settings must be added below to
    # the options dictionary.


def _default_password_checker(cfg, username, password):
    """ Check if a password is secure enough.
        We use a built-in check to get rid of the worst passwords.

        We do NOT use cracklib / python-crack here any more because it is
        not thread-safe (we experienced segmentation faults when using it).

        If you don't want to check passwords, use password_checker = None.

        :returns: None if there is no problem with the password,
                 some unicode object with an error msg, if the password is problematic.
    """
    # in any case, do a very simple built-in check to avoid the worst passwords
    if len(password) < 6:
        return _("Password is too short.")
    if len(set(password)) < 4:
        return _("Password has not enough different characters.")

    username_lower = username.lower()
    password_lower = password.lower()
    if username in password or password in username or \
       username_lower in password_lower or password_lower in username_lower:
        return _("Password is too easy to guess (password contains name or name contains password).")

    keyboards = (ur"`1234567890-=qwertyuiop[]\asdfghjkl;'zxcvbnm,./",  # US kbd
                 ur"^1234567890ß´qwertzuiopü+asdfghjklöä#yxcvbnm,.-",  # german kbd
                )  # TODO add more keyboards!
    for kbd in keyboards:
        rev_kbd = kbd[::-1]
        if password in kbd or password in rev_kbd or \
           password_lower in kbd or password_lower in rev_kbd:
            return _("Password is too easy to guess (keyboard sequence).")
    return None


class DefaultExpression(object):
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
  'datastruct': ('Datastruct', None, (
    #('dicts', lambda cfg: datastruct.ConfigDicts({}),
    ('dicts', lambda cfg: datastruct.WikiDicts(),
     "function f(cfg) that returns a backend which is used to access dicts definitions."),
    #('groups', lambda cfg: datastruct.ConfigGroups({}),
    ('groups', lambda cfg: datastruct.WikiGroups(),
     "function f(cfg) that returns a backend which is used to access groups definitions."),
  )),
  # ==========================================================================
  'auth': ('Authentication / Authorization / Security', None, (
    ('auth', DefaultExpression('[MoinAuth()]'),
     "list of auth objects, to be called in this order (see HelpOnAuthentication)"),
    ('secrets', None, """Either a long shared secret string used for multiple purposes or a dict {"purpose": "longsecretstring", ...} for setting up different shared secrets for different purposes."""),
    ('SecurityPolicy',
     DefaultSecurityPolicy,
     "Class object hook for implementing security restrictions or relaxations"),
    ('endpoints_excluded',
     [],
     "Exclude unwanted endpoints (list of strings)"),

    ('password_checker', DefaultExpression('_default_password_checker'),
     'checks whether a password is acceptable (default check is length >= 6, at least 4 different chars, no keyboard sequence, not username used somehow (you can switch this off by using `None`)'),

    ('passlib_crypt_context', dict(
        # schemes we want to support (or deprecated schemes for which we still have
        # hashes in our storage).
        # note about bcrypt: it needs additional code (that is not pure python and
        # thus either needs compiling or installing platform-specific binaries)
        schemes=["sha512_crypt", ],
        # default scheme for creating new pw hashes (if not given, passlib uses first from schemes)
        #default="sha512_crypt",
        # deprecated schemes get auto-upgraded to the default scheme at login
        # time or when setting a password (including doing a moin account pwreset).
        #deprecated=["auto"],
        # vary rounds parameter randomly when creating new hashes...
        #all__vary_rounds=0.1,
     ),
     "passlib CryptContext arguments, see passlib docs"),
  )),
  # ==========================================================================
  'spam_leech_dos': ('Anti-Spam / Leech / DOS',
  'These settings help limiting ressource usage and avoiding abuse.',
  (
    ('textchas', None,
     "Spam protection setup using site-specific questions/answers, see HelpOnSpam."),
    ('textchas_expiry_time', 600,
     "Time [s] for a !TextCha to expire."),
  )),
  # ==========================================================================
  'style': ('Style / Theme / UI',
  'These settings control how the wiki user interface will look like.',
  (
    ('sitename', u'Untitled Wiki',
     "Short description of your wiki site, displayed below the logo on each page, and used in RSS documents as the channel title [Unicode]"),
    ('interwikiname', None, "unique, stable and required InterWiki name (prefix, moniker) of the site [Unicode]"),
    ('html_pagetitle', None, "Allows you to set a specific HTML page title (if None, it defaults to the value of `sitename`) [Unicode]"),
    ('navi_bar', [
        ('wikilink', 'frontend.show_root', dict(), L_('Home'), L_('Home Page')),
        ('wikilink', 'frontend.global_history', dict(), L_('History'), L_('Global History')),
        ('wikilink', 'frontend.index', dict(), L_('Index'), L_('Global Index')),
        ('wikilink', 'frontend.global_tags', dict(), L_('Tags'), L_('Global Tags Index')),
        ('wikilink', 'admin.index_user', dict(), L_('User'), L_('User')),
        ('wikilink', 'admin.index', dict(), L_('Admin'), L_('Administration & Docs')),
     ],
     'Data to create the navi_bar from. Users can add more items in their quick links in user preferences. You need to configure a list of tuples (css_class, endpoint, args, label, title). Use L_() for translating. [list of tuples]'),

    ('theme_default', u'modernized', "Default theme."),

    ('serve_files', {},
     """
     Dictionary of name: filesystem_path for static file resources to serve
     from the filesystem as url .../+serve/<name>/...
     """),

    ('supplementation_item_names', [u'Discussion', ],
     "List of names of the supplementation (sub)items [Unicode]"),

    ('interwiki_preferred', [], "In dialogues, show those wikis at the top of the list [list of Unicode]."),
    ('sistersites', [], "list of tuples `('WikiName', 'sisterpagelist_fetch_url')`"),

    ('trail_size', 5,
     "Number of items in the trail of recently visited items"),

    ('item_views', [
        # (endpointname, label, check_item_exists
        ('frontend.show_item', L_('Show'), L_('Show'), False, ),
        ('frontend.download_item', L_('Download'), L_('Download'), True, ),
        ('frontend.history', L_('History'), L_('Revision History'), True, ),
        # note: when rendering a non-existing item, you'll be offered to
        # create it (in the content area), so we do not offer "Modify":
        ('frontend.modify_item', L_('Modify'), L_('Edit or Upload'), True, ),
        ('special.supplementation', None, None, False, ),
        ('frontend.index', L_('Index'), L_('List sub-items'), False, ),
        ('special.comments', L_('Comments'), L_('Hide comments'), True, ),
        ('special.transclusions', L_('Transclusions'), L_('Show transclusions'), True, ),
        ('frontend.highlight_item', L_('Highlight'), L_('Show with Syntax-Highlighting'), True, ),
        ('frontend.show_item_meta', L_('Meta'), L_('Display Metadata'), True, ),
        ('frontend.quicklink_item', None, L_('Create or remove a navigation link to this item'), False, ),
        ('frontend.subscribe_item', None, L_('Switch notifications about item changes on or off'), False, ),
        ('frontend.rename_item', L_('Rename'), L_('Rename this item'), True, ),
        ('frontend.delete_item', L_('Delete'), L_('Delete this item'), True, ),
        ('frontend.destroy_item', L_('Destroy'), L_('Completely destroy this item'), True, ),
        ('frontend.backrefs', L_('Referrers'), L_('What refers here?'), False, ),
        ('frontend.sitemap', L_('Site Map'), L_('Local Site Map of this item'), True, ),
        ('frontend.similar_names', L_('Similar'), L_('Items with similar names'), False, ),
     ],
     'list of edit bar entries (list of tuples (endpoint, label))'),

    ('show_hosts', True,
     "if True, show host names and IPs. Set to False to hide them."),
    ('show_interwiki', False,
     "if True, let the theme display your interwiki name"),
    ('show_names', True,
     "if True, show user names in the revision history and on Recent``Changes. Set to False to hide them."),
    ('show_section_numbers', False,
     'show section numbers in headings by default'),
    ('show_rename_redirect', False, "if True, offer creation of redirect pages when renaming wiki pages"),

    ('template_dirs', [], "list of directories with templates that will override theme and base templates."),
  )),
  # ==========================================================================
  'editor': ('Editor', None, (
    ('item_license', u'', 'if set, show the license item within the editor. [Unicode]'),
    #('edit_locking', 'warn 10', "Editor locking policy: `None`, `'warn <timeout in minutes>'`, or `'lock <timeout in minutes>'`"),
    ('edit_ticketing', True, None),
  )),
  # ==========================================================================
  'paging': ('Paging', None, (
    ('results_per_page', 50, "Number of results to be shown on a single page in pagination"),
  )),
  # ==========================================================================
  'data': ('Data Storage', None, (
    ('data_dir', './data/', "Path to the data directory."),
    ('plugin_dirs', [], "Plugin directories."),

    ('interwiki_map', {},
     "Dictionary of wiki_name -> wiki_url"),
    ('namespace_mapping', None,
    "A list of tuples, each tuple containing: Namespace identifier, backend name. " +
    "E.g.: [('', 'default')), ]. Please see HelpOnStorageConfiguration for further reference."),
    ('backend_mapping', None,
    "A dictionary that maps backend names to backends. " +
    "E.g.: {'default': Backend(), }. Please see HelpOnStorageConfiguration for further reference."),
    ('acl_mapping', None,
    "This needs to point to a list of tuples, each tuple containing: name prefix, acl protection to be applied to matching items. " +
    "E.g.: [('', dict(default='All:read,write,create')), ]. Please see HelpOnStorageConfiguration for further reference."),
    ('create_storage', False, "Create (initialize) the storage backends before trying to use them."),
    ('create_index', False, "Create (initialize) the index before trying to use them."),
    ('destroy_storage', False, "Destroy (empty) the storage backends after using them."),
    ('destroy_index', False, "Destroy (empty) the index after using it."),
  )),
  # ==========================================================================
  'items': ('Special Item Names', None, (
    ('item_root', u'Home', "Name of the root item (aka 'front page'). [Unicode]"),

    # the following regexes should match the complete name when used in free text
    # the group 'all' shall match all, while the group 'key' shall match the key only
    # e.g. FooGroup -> group 'all' ==  FooGroup, group 'key' == Foo
    # moin's code will add ^ / $ at beginning / end when needed
    ('item_dict_regex', ur'(?P<all>(?P<key>\S+)Dict)',
     'Item names exactly matching this regex are regarded as items containing variable dictionary definitions [Unicode]'),
    ('item_group_regex', ur'(?P<all>(?P<key>\S+)Group)',
     'Item names exactly matching this regex are regarded as items containing group definitions [Unicode]'),
  )),
  # ==========================================================================
  'user': ('User Preferences', None, (
    ('user_defaults',
      dict(
        name=[],
        display_name=None,
        email=None,
        openid=None,
        css_url=None,
        mailto_author=False,
        edit_on_doubleclick=True,
        scroll_page_after_edit=True,
        show_comments=False,
        want_trivial=False,
        enc_password=u'',  # empty value == invalid hash
        disabled=False,
        bookmarks={},
        quicklinks=[],
        subscribed_items=[],
        email_subscribed_events=[
            # XXX PageChangedEvent.__name__
            # XXX PageRenamedEvent.__name__
            # XXX PageDeletedEvent.__name__
            # XXX PageCopiedEvent.__name__
            # XXX PageRevertedEvent.__name__
        ],
        theme_name=None,  # None -> use cfg.theme_default
        edit_rows=0,
        results_per_page=0,
        locale=None,  # None -> do browser language detection, otherwise just use this locale
        timezone=None,  # None -> use cfg.timezone_default
      ),
     'Default attributes of the user object'),
  )),
  # ==========================================================================
  'various': ('Various', None, (
    ('bang_meta', True, 'if True, enable {{{!NoWikiName}}} markup'),

    ('config_check_enabled', False, "if True, check configuration for unknown settings."),

    ('timezone_default', u'UTC', "Default time zone."),
    ('locale_default', u'en_US', "Default locale for user interface and content."),

    ('log_remote_addr', True,
     "if True, log the remote IP address (and maybe hostname)."),
    ('log_reverse_dns_lookups', True,
     "if True, do a reverse DNS lookup on page SAVE. If your DNS is broken, set this to False to speed up SAVE."),

    # some dangerous mimetypes (we don't use "content-disposition: inline" for them when a user
    # downloads such data, because the browser might execute e.g. Javascript contained
    # in the HTML and steal your moin session cookie or do other nasty stuff)
    ('mimetypes_xss_protect',
     [
       'text/html',
       'application/x-shockwave-flash',
       'application/xhtml+xml',
     ],
     '"content-disposition: inline" is not used for downloads of such data'),

    ('refresh', None,
     "refresh = (minimum_delay_s, targets_allowed) enables use of `#refresh 5 PageName` processing instruction, targets_allowed must be either `'internal'` or `'external'`"),

    ('siteid', 'MoinMoin', None),  # XXX just default to some existing module name to
                                   # make plugin loader etc. work for now
  )),
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
# All the help texts will be displayed by the WikiConfigHelp() macro.
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
    'acl': ('Access Control Lists',
    'ACLs control who may do what.',
    (
      ('functions', u'',
       'Access Control List for functions.'),
      ('rights_contents', ACL_RIGHTS_CONTENTS,
       'Valid tokens for right sides of content ACL entries.'),
      ('rights_functions', ACL_RIGHTS_FUNCTIONS,
       'Valid tokens for right sides of function ACL entries.'),
    )),

    'ns': ('Storage Namespaces',
    "Storage namespaces can be defined for all sorts of data. All items sharing a common namespace as prefix" +
    "are then stored within the same backend. The common prefix for all data is ''.",
    (
      ('content', '/', "All content is by default stored below /, hence the prefix is ''."),  # Not really necessary. Just for completeness.
      ('user_profile', 'UserProfile/', 'User profiles (i.e. user data, not their homepage) are stored in this namespace.'),
      ('user_homepage', 'User/', 'All user homepages are stored below this namespace.'),
    )),

    'user': ('User', None, (
      ('email_unique', True,
       "if True, check email addresses for uniqueness and don't accept duplicates."),
      ('email_verification', False,
       "if True, require a new user to verify his or her email address before the first login."),

      ('homewiki', u'Self',
       "interwiki name of the wiki where the user home pages are located [Unicode] - useful if you have ''many'' users. You could even link to nonwiki \"user pages\" if the wiki username is in the target URL."),
      ('use_gravatar', False, "if True, gravatar.com will be used to find User's avatar")
    )),

    'mail': ('Mail',
        'These settings control outgoing and incoming email from and to the wiki.',
    (
      ('from', None, "Used as From: address for generated mail. [Unicode]"),
      ('username', None, "Username for SMTP server authentication (None = don't use auth)."),
      ('password', None, "Password for SMTP server authentication (None = don't use auth)."),
      ('smarthost', None, "Address of SMTP server to use for sending mail (None = don't use SMTP server)."),
      ('sendmail', None, "sendmail command to use for sending mail (None = don't use sendmail)"),
    )),
}


def _add_options_to_defconfig(opts, addgroup=True):
    for groupname in opts:
        group_short, group_doc, group_opts = opts[groupname]
        for name, default, doc in group_opts:
            if addgroup:
                name = groupname + '_' + name
            if isinstance(default, DefaultExpression):
                default = default.value
            setattr(DefaultConfig, name, default)

_add_options_to_defconfig(options)
_add_options_to_defconfig(options_no_group_name, False)
