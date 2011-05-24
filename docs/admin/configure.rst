========================================
Introduction into MoinMoin Configuration
========================================
Kinds of configuration files
============================
To change how moin behaves and looks like, you may customize it by editing
its misc. configuration files:

* Wiki Engine Configuration

  - the file is often called wikiconfig.py, but it can have any name
  - in that file, there is a Config class - this is the wiki engine's config
  - this is Python code

* Framework Configuration
  
  - this is also located in the same file as the Wiki Engine Configuration
  - there are some UPPERCASE settings at the bottom - this is the framework's
    config (for Flask and Flask extensions)
  - this is Python code

* Logging Configuration

  - optional, if you don't configure this, it'll use builtin defaults
  - this is a separate file, often called logging.conf or so
  - .ini-like file format

Do small steps and have backups
-------------------------------
It is a good idea to start from one of the sample configs provided with moin
and only do small careful changes, then trying it, then doing next change.

If you're not used to the config file format, backup your last working config
so you can revert to it in case you make some hard to find typo or other error.

Editing Python files
--------------------
When editing Python files, be careful with indentation, only use multiples of
4 spaces to indent, no tabs!

Also, be careful with syntax in general, it must be valid python code or else
it'll crash with some error when trying to load the config. If that happens,
read the error message, it'll usually tell the line number and what the problem
is. If you can't fix it easily, just revert to your backup of your last working
config.

Why Python for configuration?
-----------------------------
At first, you might wonder why we use Python code for configuration. It is
simply because it is powerful and we can make use of that power there.
Using something else would usually mean much more work when developing new
stuff and also would be much less flexible and powerful, dumbing down
everything.

wikiconfig.py Layout
====================

A wikiconfig.py looks like this::

 # -*- coding: utf-8 -*-
 from MoinMoin.config.default import DefaultConfig

 class Config(DefaultConfig):
     # a comment
     sometext = u'your value'
     somelist = [1, 2, 3]

 MOINCFG = Config  # Flask only likes uppercase stuff
 SOMETHING_FLASKY = 'foobar'

Let's go through this line-by-line:

0. this declares the encoding of the config file. make sure your editor uses
   the same encoding (character set), esp. if you intend to use non-ASCII
   characters (e.g. non-english stuff).
1. this gets the DefaultConfig class from the moin code - it has default
   values for all settings (this will save you work, you only have to define
   stuff you want different from the default).
2. an empty line, for better readability
3. now we define a new class `Config` that inherits most stuff from
   `DefaultConfig` - this is the wiki engine configuration. If you define some
   setting within this class, it'll overwrite the setting from DefaultConfig.
4. with a `#` character you can write a comment into your config. This line (as
   well as all other following lines with Config settings) is indented by 4
   blanks, because Python defines blocks by indentation.
5. define a Config attribute called `sometext` with value u'your value' -
   the `u'...'` means that this is a unicode string.
6. define a Config attribute called `somelist` with value [1, 2, 3] - this is
   a list with the numbers 1, 2 and 3 as list elements.
7. empty line, for better readability
8. The special line "MOINCFG = Config" must stay there in exactly this form due to
   technical reasons.
9. UPPERCASE stuff at the bottom, outside the Config class - this is framework
   configuration (usually something for Flask or some Flask extension).

A real-life example of a `wikiconfig.py` can be found in the
`docs/examples/config/` directory.

=========================
Wiki Engine Configuration
=========================

User Interface Customization
============================

Using a custom snippets.html template
-------------------------------------
Some user interface or html elements that often need customization are
defined as macros in the template file `snippets.html`.

If you'ld like to customize some stuff, you have to make a copy of the built-in
`MoinMoin/templates/snippets.html` and configure moin so it will prefer your
copy instead of the built-in one.

This is done by just giving a list of template directories where moin will
look first::

    template_dirs = ['path/to/my/templates', ]

To customize something, you usually have to insert your stuff between the
`{% macro ... %}` and `{% endmacro %}` lines, see below for more details.

Logo
~~~~
To replace the default MoinMoin logo with your own logo (which is **strongly**
recommended, especially if your wiki has private or sensitive information),
so your users will immediately recognize which wiki site they currently use.

You can even use some simple text (or just nothing) for the logo, it is not
required to be an image.

Make sure the dimensions of your logo image or text fit into the layout of
the theme(s) your wiki users are using.

Example code::

    {% macro logo() -%}
    <img src="http://wiki.example.org/logos/my_logo.png" id="moin-img-logo" alt="Example Logo">
    {%- endmacro %}

Displaying license information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you need to display something like a license information for your content or
some other legalese, use this macro to do it::

    {# License information in the footer #}
    {% macro license_info() -%}
    All wiki content is licensed under the WTFPL.
    {%- endmacro %}

Inserting pieces of HTML
~~~~~~~~~~~~~~~~~~~~~~~~
At some specific places, you can just add a piece of own html into the
head or body of the theme's html output::

    {# Additional HTML tags inside <head> #}
    {% macro head() -%}
    {%- endmacro %}

    {# Additional HTML before #moin-header #}
    {% macro before_header() -%}
    {%- endmacro %}

    {# Additional HTML after #moin-header #}
    {% macro after_header() -%}
    {%- endmacro %}

    {# Additional HTML before #moin-footer #}
    {% macro before_footer() -%}
    {%- endmacro %}

    {# Additional HTML after #moin-footer #}
    {% macro after_footer() -%}
    {%- endmacro %}

Credits and Credit Logos
~~~~~~~~~~~~~~~~~~~~~~~~
At the bottom, we usually show some text and image links pointing out that
this wiki runs MoinMoin, uses Python, that MoinMoin is GPL licensed, etc.

If you run a public site using MoinMoin, we would appreciate if you please
*keep* those links (esp. the "MoinMoin powered" one).

However, if you can't do that for some reason, feel free to modify these
macros to show whatever you want::

    {# Image links in the footer #}
    {% macro creditlogos(start='<ul id="moin-creditlogos"><li>'|safe, end='</li></ul>'|safe, sep='</li><li>'|safe) %}
    {{ start }}
    {{ creditlogo('http://moinmo.in/', url_for('.static', filename='logos/moinmoin_powered.png'),
       'MoinMoin powered', 'This site uses the MoinMoin Wiki software.') }}
    {{ sep }}
    {{ creditlogo('http://moinmo.in/Python', url_for('.static', filename='logos/python_powered.png'),
       'Python powered', 'MoinMoin is written in Python.') }}
    {{ end }}
    {% endmacro %}

    {# Text links in the footer #}
    {% macro credits(start='<p id="moin-credits">'|safe, end='</p>'|safe, sep='<span>&bull;</span>'|safe) %}
    {{ start }}
    {{ credit('http://moinmo.in/', 'MoinMoin Powered', 'This site uses the MoinMoin Wiki software.') }}
    {{ sep }}
    {{ credit('http://moinmo.in/Python', 'Python Powered', 'MoinMoin is written in Python.') }}
    {{ sep }}
    {{ credit('http://moinmo.in/GPL', 'GPL licensed', 'MoinMoin is GPL licensed.') }}
    {{ sep }}
    {{ credit('http://validator.w3.org/check?uri=referer', 'Valid HTML 5', 'Click here to validate this page.') }}
    {{ end }}
    {% endmacro %}

Adding scripts
~~~~~~~~~~~~~~
You can add scripts like this::

    {# Additional Javascript #}
    {% macro scripts() -%}
    <script type="text/javascript" src="http://example.org/cool.js"></script>
    {% endmacro %}

Adding CSS
~~~~~~~~~~
If you just want some style changes, you maybe can do them by just adding
some custom css (and overwrite any style you don't like in the base theme)::

    {# Additional Stylesheets (after theme css, before user css #}
    {% macro stylesheets() -%}
        <link media="screen" href="http://wiki.example.org/static/company.css" title="Company CSS" rel="stylesheet" />
        <link media="screen" href="http://wiki.example.org/static/red.css" title="Red Style" rel="alternate stylesheet" />
        <link media="screen" href="http://wiki.example.org/static/green.css" title="Green Style" rel="alternate stylesheet" />
    {%- endmacro %}

You can either just add some normal css stylesheet or add a choice of alternate
stylesheets.

See:

* `CSS media types <http://www.w3.org/TR/CSS2/media.html>`_
* `Alternate Stylesheets <http://www.alistapart.com/articles/alternate/>`_

A good way to test a stylesheet is to first use it as user CSS before you
configure it for everybody.

Please note that `stylesheets` will be included no matter what theme the wiki
user has selected, so maybe either only do changes applying to all available
themes or force all users to use same theme, so that your CSS applies
correctly.


Custom Themes
-------------
In case you want to do major changes to how MoinMoin looks like (so just
changing snippets or CSS is not enough), you could also write your own theme.

Be warned: doing this is a long-term thing, you don't just have to write it,
but you'll also have to maintain and update it. Thus, we suggest you try
living with the built-in themes or collaborate with the MoinMoin core and
other interested developers on the internet.

A few well-made, well-maintained and widespread themes are much better than
lots of the opposite.

.. todo::

   Add more details about custom themes


Authentication
==============
MoinMoin uses a configurable `auth` list of authenticators, so the admin can
configure whatever he likes to allow for authentication. Moin processes this
list from left to right.

Each authenticator is an instance of some specific class, configuration of
the authenticators usually works by giving them keyword arguments. Most have
reasonable defaults, though.

MoinAuth
--------
This is the default authentication moin uses if you don't configure something
else. The user logs in by filling out the login form with username and
password, moin compares the password hash against the one stored in the user's
profile and if both match, the user is authenticated::

    from MoinMoin.auth import MoinAuth
    auth = [MoinAuth()]  # this is the default!

HTTPAuthMoin
------------
With HTTPAuthMoin moin does http basic auth all by itself (without help of
the web server)::

    from MoinMoin.auth.http import HTTPAuthMoin
    auth = [HTTPAuthMoin(autocreate=True)]

If configured like that, moin will request authentication by emitting a
http header. Browsers then usually show some login dialogue to the user,
asking for username and password. Both then gets transmitted to moin and it
is compared against the password hash stored in the user's profile.

Note: when HTTPAuthMoin is used, the browser will show that login dialogue, so
users must login to use the wiki.

GivenAuth
---------
With GivenAuth moin relies on the webserver doing the authentication and giving
the result to moin (usually via environment variable REMOTE_USER)::

    from MoinMoin.auth import GivenAuth
    auth = [GivenAuth(autocreate=True, coding='utf-8')]

Using this has some pros and cons:

* you can use lots of authentication extensions available for your web server
* but the only information moin will get (via REMOTE_USER) is the authenticated
  user's name, nothing else. So, e.g. for LDAP/AD, you won't get additional
  stuff stored in the LDAP directory.
* all the stuff you won't get (but you need) will need to be manually stored
  and updated in the user's profile (e.g. the user's email address, etc.)

Please note that you must give the correct coding (character set) so that moin
can decode the username to unicode, if necessary. For environment variables
like REMOTE_USER, the coding might depend on your operating system.

If you do not know the correct coding, try: 'utf-8', 'iso-8859-1', ...

.. todo::

   add the usual coding(s) for some platforms (like windows)

To try it out, change configuration, restart moin and then use some non-ASCII
username (like with german umlauts or accented characters). If moin does not
crash (log a Unicode Error), you have likely found the correct coding.

OpenID
------
With OpenID moin can re-use the authentication done by some OpenID provider
(like Google, Yahoo, Microsoft or others)::

    from MoinMoin.auth.openidrp import OpenIDAuth
    auth = [OpenIDAuth()]

By default OpenID authentication accepts all OpenID providers. If you
like, you can configure what providers to allow (which ones you want to trust)
by adding their URLs to the trusted_providers keyword of OpenIDAuth. If left
empty, moin will allow all providers::

    # Allow google profile OpenIDs only:
    auth = [OpenIDAuth(trusted_providers=['https://www.google.com/accounts/o8/ud?source=profiles'])]

To be able to log in with OpenID, the user needs to have his OpenID stored
in his user profile.

LDAPAuth
--------
With LDAPAuth you can authenticate users against a LDAP directory or MS Active Directory service.

LDAPAuth with single LDAP server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This example shows how to use it with a single LDAP/AD server::

    from MoinMoin.auth.ldap_login import LDAPAuth
    ldap_common_arguments = dict(
        # the values shown below are the DEFAULT values (you may remove them if you are happy with them),
        # the examples shown in the comments are typical for Active Directory (AD) or OpenLDAP.
        bind_dn='',  # We can either use some fixed user and password for binding to LDAP.
                     # Be careful if you need a % char in those strings - as they are used as
                     # a format string, you have to write %% to get a single % in the end.
                     #bind_dn = 'binduser@example.org' # (AD)
                     #bind_dn = 'cn=admin,dc=example,dc=org' # (OpenLDAP)
                     #bind_pw = 'secret'
                     # or we can use the username and password we got from the user:
                     #bind_dn = '%(username)s@example.org' # DN we use for first bind (AD)
                     #bind_pw = '%(password)s' # password we use for first bind
                     # or we can bind anonymously (if that is supported by your directory).
                     # In any case, bind_dn and bind_pw must be defined.
        bind_pw='',
        base_dn='',  # base DN we use for searching
                     #base_dn = 'ou=SOMEUNIT,dc=example,dc=org'
        scope=2, # scope of the search we do (2 == ldap.SCOPE_SUBTREE)
        referrals=0, # LDAP REFERRALS (0 needed for AD)
        search_filter='(uid=%(username)s)',  # ldap filter used for searching:
                                             #search_filter = '(sAMAccountName=%(username)s)' # (AD)
                                             #search_filter = '(uid=%(username)s)' # (OpenLDAP)
                                             # you can also do more complex filtering like:
                                             # "(&(cn=%(username)s)(memberOf=CN=WikiUsers,OU=Groups,DC=example,DC=org))"
        # some attribute names we use to extract information from LDAP (if not None,
        # if None, the attribute won't be extracted from LDAP):
        givenname_attribute=None, # often 'givenName' - ldap attribute we get the first name from
        surname_attribute=None, # often 'sn' - ldap attribute we get the family name from
        aliasname_attribute=None, # often 'displayName' - ldap attribute we get the aliasname from
        email_attribute=None, # often 'mail' - ldap attribute we get the email address from
        email_callback=None, # callback function called to make up email address
        coding='utf-8', # coding used for ldap queries and result values
        timeout=10, # how long we wait for the ldap server [s]
        start_tls=0, # usage of Transport Layer Security 0 = No, 1 = Try, 2 = Required
        tls_cacertdir=None,
        tls_cacertfile=None,
        tls_certfile=None,
        tls_keyfile=None,
        tls_require_cert=0, # 0 == ldap.OPT_X_TLS_NEVER (needed for self-signed certs)
        bind_once=False, # set to True to only do one bind - useful if configured to bind as the user on the first attempt
        autocreate=True, # set to True to automatically create/update user profiles
        report_invalid_credentials=True, # whether to emit "invalid username or password" msg at login time or not
    )

    ldap_authenticator1 = LDAPAuth(
        server_uri='ldap://localhost',  # ldap / active directory server URI
                                        # use ldaps://server:636 url for ldaps,
                                        # use  ldap://server for ldap without tls (and set start_tls to 0),
                                        # use  ldap://server for ldap with tls (and set start_tls to 1 or 2).
        name='ldap1',  # unique name for the ldap server, e.g. 'ldap_pdc' and 'ldap_bdc' (or 'ldap1' and 'ldap2')
        **ldap_common_arguments  # expand the common arguments
    )

    auth = [ldap_authenticator1, ] # this is a list, you may have multiple ldap authenticators
                                   # as well as other authenticators

    # customize user preferences (optional, see MoinMoin/config/multiconfig for internal defaults)
    # you maybe want to use user_checkbox_remove, user_checkbox_defaults, user_form_defaults,
    # user_form_disable, user_form_remove.

LDAPAuth with two LDAP servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This example shows how to use it with a two LDAP/AD servers (like e.g. a primary
and backup domain controller)::

    # ... same stuff as for single server (except the line with "auth =") ...
    ldap_authenticator2 = LDAPAuth(
        server_uri='ldap://otherldap',  # ldap / active directory server URI for second server
        name='ldap2',
        **ldap_common_arguments
    )

    auth = [ldap_authenticator1, ldap_authenticator2, ]

AuthLog
-------
AuthLog is no real authenticator in the sense that it authenticates (logs in) or
deauthenticates (logs out) users, it is just passively logging informations for
authentication debugging::

    from MoinMoin.auth import MoinAuth
    from MoinMoin.auth.log import AuthLog
    auth = [MoinAuth(), AuthLog(), ]

Example logging output::

 2011-02-05 16:35:00,229 INFO MoinMoin.auth.log:22 login: user_obj=<MoinMoin.user.User at 0x90a0f0c name:u'ThomasWaldmann' valid:1> kw={'username': u'ThomasWaldmann', 'openid': None, 'attended': True, 'multistage': None, 'login_password': u'secret', 'login_username': u'ThomasWaldmann', 'password': u'secret', 'login_submit': u''}
 2011-02-05 16:35:04,716 INFO MoinMoin.auth.log:22 session: user_obj=<MoinMoin.user.User at 0x90a0f6c name:u'ThomasWaldmann' valid:1> kw={}
 2011-02-05 16:35:06,294 INFO MoinMoin.auth.log:22 logout: user_obj=<MoinMoin.user.User at 0x92b5d4c name:u'ThomasWaldmann' valid:False> kw={}
 2011-02-05 16:35:06,328 INFO MoinMoin.auth.log:22 session: user_obj=None kw={}

Note: there are sensitive informations like usernames and passwords in this
log output. Make sure you only use this for testing and delete the logs when
done.

SMBMount
--------
SMBMount is no real authenticator in the sense that it authenticates (logs in)
or deauthenticates (logs out) users. It just catches the username and password
and uses them to mount a SMB share as this user.

SMBMount is only useful for very special applications, e.g. in combination
with the fileserver storage backend::

    from MoinMoin.auth.smb_mount import SMBMount

    smbmounter = SMBMount(
        # you may remove default values if you are happy with them
        # see man mount.cifs for details
        server='smb.example.org',  # (no default) mount.cifs //server/share
        share='FILESHARE',  # (no default) mount.cifs //server/share
        mountpoint_fn=lambda username: u'/mnt/wiki/%s' % username,  # (no default) function of username to determine the mountpoint
        dir_user='www-data',  # (no default) username to get the uid that is used for mount.cifs -o uid=...
        domain='DOMAIN',  # (no default) mount.cifs -o domain=...
        dir_mode='0700',  # (default) mount.cifs -o dir_mode=...
        file_mode='0600',  # (default) mount.cifs -o file_mode=...
        iocharset='utf-8',  # (default) mount.cifs -o iocharset=... (try 'iso8859-1' if default does not work)
        coding='utf-8',  # (default) encoding used for username/password/cmdline (try 'iso8859-1' if default does not work)
        log='/dev/null',  # (default) logfile for mount.cifs output
    )

    auth = [....., smbmounter]  # you need a real auth object in the list before smbmounter

    smb_display_prefix = u"S:"  # where //server/share is usually mounted for your windows users (display purposes only)

.. todo::

   check if SMBMount still works as documented


Transmission security
=====================
Credentials
-----------
Some of the authentication methods described above will transmit credentials
(like usernames and password) in unencrypted form:

* MoinAuth: when the login form contents are transmitted to moin, they contain
  username and password in cleartext.
* HTTPAuthMoin: your browser will transfer username and password in a encoded
  (but NOT encrypted) form with EVERY request (it uses http basic auth).
* GivenAuth: please check the potential security issues of the authentication
  method used by your web server. For http basic auth please see HTTPAuthMoin.
* OpenID: please check yourself.

Contents
--------
http transmits everything in cleartext (not encrypted).

Encryption
----------
Transmitting unencrypted credentials or contents is a serious issue in many
scenarios.

We recommend you make sure connections are encrypted, like with https or VPN
or an ssh tunnel.

For public wikis with very low security / privacy needs, it might not be needed
to encrypt their content transmissions, but there is still an issue for the
credential transmissions.

When using unencrypted connections, wiki users are advised to make sure they
use unique credentials (== not reusing passwords that are also used for other
stuff).


Password security
=================
Password strength
-----------------
As you might know, many users are bad at choosing reasonable passwords and some
are tempted to use passwords like 123456 everywhere.

To help the users choose reasonable passwords, moin has a simple builtin
password checker that does some sanity checks (the checker is enabled by
default), so users don't choose too short or too easy passwords.

If you don't like this and your site has rather low security requirements,
feel free to DISABLE the checker by::

    password_checker = None # no password checking

Note that the builtin password checker only does a few very fundamental
checks, it e.g. won't forbid using a dictionary word as password.

Password storage
----------------
Moin never stores passwords in cleartext, but always as cryptographic hash
with random salt (currently ssha256 is the default).


Authorization
=============
Moin uses Access Control Lists (ACLs) to specify who is authorized to do
something.

Please note that wikis usually make much use of so-called *soft security*,
that means that they are rather open and give freedom to the users, while
providing means to revert damage in case it happens.

*Hard security* means to lock stuff so that no damage can happen.

Moin's default configuration tries to give a sane compromise of both soft
and hard security. But, depending on the situation the wiki
admin/owner/community has to deal with, you may need different settings.

So just keep in mind:

* if your wiki is rather open, you make it easy to contribute (like e.g. a
  user who is not a regular user of your wiki could fix some typos he has just
  found). But: a hostile user (or bot) also might put some spam into your wiki
  (you can revert the spam later).
* if you are rather closed (like requiring every user to first apply for an
  account and to log in before being able to do changes), you'll never get
  contributions from casual users and maybe also less from members of your
  community. But: likely you won't get spam either.
 

ACL for functions
-----------------
This ACL controls access to some specific functions / views of moin::

    # we just show the default value of acl_rights_functions for information,
    # you usually do not have to change it:
    #acl_rights_functions = ['superuser', 'notextcha', ]
    acl_functions = u'+YourName:superuser TrustedEditorGroup:notextcha'

Supported capabilities (rights):

* superuser - used for misc. administrative functions, give this only to
  highly trusted people
* notextcha - if you have TextChas enabled, users with notextcha capability
  won't get questions to answer. Give this to known and trusted users who
  regularly edit in your wiki.

ACLs for contents
-----------------
These ACLs control access to contents stored in the wiki - they are configured
per storage backend (see also there) and (optionally) in the metadata of wiki
items::

    # we just show the default value of acl_rights_contents for information,
    # you usually do not have to change it:
    #acl_rights_contents = ['read', 'write', 'create', 'destroy', 'admin', ]
    ... backend configuration ...
    ... before=u'YourName:read,write,create,destroy,admin',
    ... default=u'All:read,write,create',
    ... after=u'',
    ... hierarchic=False,

Usually, you have a `before`, `on item` or `default` and a `after` ACL which
are processed exactly in this order. The `default` ACL is only used if no ACL
is specified in the metadata of the item in question.

.. digraph:: acl_order

   rankdir=LR;
   "before" -> "item acl from metadata (if specified)" -> "after";
   "before" -> "default (otherwise)"                   -> "after";

How to use before/default/after:

* `before` is usually used to force stuff (e.g. if you want to give some
  wiki admin all permissions no matter what)
* `default` is behaviour if nothing special has been specified (no ACL in
  item metadata)
* `after` is (rarely) used to "not forget something unless otherwise specified".

When configuring content ACLs, you can choose between standard (flat) ACL
processing and hierarchic ACL processing. Hierarchic processing means that
subitems inherit ACLs from their parent items if they have no own ACL.

Note: while hierarchic ACLs are rather convenient sometimes, they make the
system more complex. You have to be very careful with potential permissions
changes happening due to changes in the hierarchy, like when you create,
rename or delete items.

Supported capabilities (rights):

* read - read content
* write - write (edit, modify) content
* create - create new items
* destroy - completely destroy revisions or items (never give this to not
  fully trusted users)
* admin - change (create, remove) ACLs for the item (never give this to not
  fully trusted users)

ACLs - special groups
---------------------
Additionally to the groups provided by the group backend(s), there are some
special group names available within ACLs:

* All - a virtual group containing every user
* Known - a virtual group containing every logged-in user
* Trusted - a virtual group containing every logged-in user, who was logged
  in by some specific "trusted" authentication methods


ACLs - basic syntax
-------------------
An ACL is a (unicode) string with one or multiple access control entries
(space separated).

An entry has:

* a left side with user and/or group names (comma separated)
* a colon ':' as separator and
* a right side with rights / capabilities (comma separated).

An ACL is processed from left to right, first left-side match counts.

Example::

    u"SuperMan:read,write,create,destroy,admin All:read,write"

If "SuperMan" is currently logged in and moin processes this ACL, it'll find
a name match in the first entry. If moin wants to know whether he may destroy,
the answer will be "yes", as destroy is one of the capabilities/rights listed
on the right side of this entry.

If "JoeDoe" is currently logged in and moin processes this ACL, the first entry
won't match, so moin will proceed left-to-right and look at the second entry.
Here we have the special group name "All" (and JoeDoe obviously is a member of
this group), so we have a match here.
If moin wants to know whether he may destroy, the answer will be "no", as
destroy is not listed on the right side of this entry. If moin wants to know
whether he may write, the answer will be "yes".

Notes:

* As a consequence of the left-to-right and first-match-counts processing,
  you must order ACL entries so that the more specific ones (like for
  "SuperMan") are left of the less specific ones.
  Usually you want this order:

  1) usernames
  2) special groups
  3) more general groups
  4) Trusted
  5) Known
  6) All

* Do not put any spaces into an ACL entry (except if it is part of a user or
  group name)

* A right that is not explicitly given by an applicable ACL is denied.

* For most ACLs there are builtin defaults, which give some rights.

ACLs - entry prefixes
---------------------
To make the system more flexible, there are also two ACL entry modifiers: the prefixes '+' and '-'.

If you use them, matches will have to be left-side *and* right-side (otherwise
it will just continue with the next entry).

'+' means to give the permission(s) specified on the right side.

'-' means to deny the permission(s) specified on the right side.

Example::

    u"+SuperMan:create,destroy,admin -Idiot:write All:read,write"

If "SuperMan" is currently logged in and moin wants to know whether he may
destroy, it'll find a match in the first entry (name matches *and* permission
in question matches). As the prefix is '+', the answer is "yes".
If moin wants to know whether he may write, the first entry will not match
on both sides, so moin will proceed and look at the second entry. It doesn't
match, so it'll look at the third entry. Of course "SuperMan" is a member of
group "All", so we have a match here. As "write" is listed on the right side,
the answer will be "yes".

If "Idiot" is currently logged in and moin wants to know whether he may write,
it'll find no match in the first entry, but the second entry will match. As
the prefix is '-', the answer will be "no" (and it will not even proceed and
look at the third entry).

Notes:

* you usually use these modifiers if most of the rights shall be as specified
  later, but a special user or group should be treated slightly different for
  a few special rights.

ACLs - Default entry
--------------------
There is a special ACL entry "Default" which expands itself in-place to the
default ACL.

This is useful if e.g. for some items you mostly want the default ACL, but
with a slight modification - but you don't want to type in the default ACL
all the time (and you also want to be able to change the default ACL without
having to edit lots of items).

Example::

    u"-NotThisGuy:write Default"

This will behave as usual, except that "NotThisGuy" will never be given write
permission.


Anti-Spam
=========
TextChas
--------

A TextCHA is a pure text alternative to ''CAPTCHAs''. MoinMoin uses it to
prevent wiki spamming and it has proven to be very effective.

Features:

* when registering a user or saving an item, ask a random question
* match the given answer against a regular expression
* q and a can be configured in the wiki config
* multi language support: a user gets a textcha in his language or in
  language_default or in English (depending on availability of questions and
  answers for the language)

TextCha Configuration
~~~~~~~~~~~~~~~~~~~~~

Tips for configuration:

* have 1 word / 1 number answers
* ask questions that normal users of your site are likely to be able to answer
* do not ask too hard questions
* do not ask "computable" questions, like "1+1" or "2*3"
* do not ask too common questions
* do not share your questions with other sites / copy questions from other
  sites (or spammers might try to adapt to this) 
* you should at least give textchas for 'en' (or for your language_default, if
  that is not 'en') as this will be used as fallback if MoinMoin does not find
  a textcha in the user's language

In your wiki config, do something like this::

    textchas = {
        'en': { # silly english example textchas (do not use them!)
                u"Enter the first 9 digits of Pi.": ur"3\.14159265",
                u"What is the opposite of 'day'?": ur"(night|nite)",
                # ...
        },
        'de': { # some german textchas
                u"Gib die ersten 9 Stellen von Pi ein.": ur"3\.14159265",
                u"Was ist das Gegenteil von 'Tag'?": ur"nacht",
                # ...
        },
        # you can add more languages if you like
    }


Note that users with 'notextcha' ACL capability won't get TextChas to answer.


Secrets
=======
Moin uses secrets (just use a long random strings, don't reuse any of your
passwords) to encrypt or cryptographically sign some stuff like:

* textchas
* tickets

Don't use the strings shown below, they are NOT secret as they are part of the
moin documentation - make up your own secrets::

    secrets = {
        'security/textcha': 'kjenrfiefbeiaosx5ianxouanamYrnfeorf',
        'security/ticket': 'asdasdvarebtZertbaoihnownbrrergfqe3r',
    }

If you don't configure these secrets, moin will detect this and reuse Flask's
SECRET_KEY for all secrets it needs.


Groups and Dicts
================
Moin can get group and dictionary information from some supported backends
(like the wiki configuration or wiki items).

A group is just a list of unicode names. It can be used for any application,
one application is defining user groups for usage in ACLs.

A dict is a mapping of unicode keys to unicode values. It can be used for any
application, currently it is not used by moin itself.

Group backend configuration
---------------------------
WikiGroups backend gets groups from wiki items and is used by default::

    def groups(self, request):
        from MoinMoin.datastruct import WikiGroups
        return WikiGroups(request)

ConfigGroups uses groups defined in the configuration file::

    def groups(self, request):
        from MoinMoin.datastruct import ConfigGroups
        # Groups are defined here.
        groups = {u'EditorGroup': [u'AdminGroup', u'John', u'JoeDoe', u'Editor1'],
                  u'AdminGroup': [u'Admin1', u'Admin2', u'John']}
        return ConfigGroups(request, groups)

CompositeGroups to use both ConfigGroups and WikiGroups backends::

    def groups(self, request):
        from MoinMoin.datastruct import ConfigGroups, WikiGroups, CompositeGroups
        groups = {u'EditorGroup': [u'AdminGroup', u'John', u'JoeDoe', u'Editor1'],
                  u'AdminGroup': [u'Admin1', u'Admin2', u'John']}

        # Here ConfigGroups and WikiGroups backends are used.
        # Note that order matters! Since ConfigGroups backend is mentioned first
        # EditorGroup will be retrieved from it, not from WikiGroups.
        return CompositeGroups(request,
                               ConfigGroups(request, groups),
                               WikiGroups(request))


Dict backend configuration
--------------------------

WikiDicts backend gets dicts from wiki items and is used by default::

    def dicts(self, request):
        from MoinMoin.datastruct import WikiDicts
        return WikiDicts(request)

ConfigDicts backend uses dicts defined in the configuration file::

    def dicts(self, request):
        from MoinMoin.datastruct import ConfigDicts
        dicts = {u'OneDict': {u'first_key': u'first item',
                              u'second_key': u'second item'},
                 u'NumbersDict': {u'1': 'One',
                                  u'2': 'Two'}}
        return ConfigDicts(request, dicts)

CompositeDicts to use both ConfigDicts and WikiDicts::

    def dicts(self, request):
        from MoinMoin.datastruct import ConfigDicts, WikiDicts, CompositeDicts
        dicts = {u'OneDict': {u'first_key': u'first item',
                              u'second_key': u'second item'},
                 u'NumbersDict': {u'1': 'One',
                                  u'2': 'Two'}}
        return CompositeDicts(request,
                              ConfigDicts(request, dicts),
                              WikiDicts(request))


Storage
=======
MoinMoin supports storage backends for different ways of storing wiki items.

Setup of storage is rather complex and layered, involving:

* a router middleware that dispatches parts of the namespace to the respective
  backend
* ACL checking middlewares that make sure nobody accesses something he is not
  authorized to access
* Indexing mixin that indexes some data automatically on commit, so items can
  be selected / retrieved faster.
* storage backends that really store wiki items somewhere

create_simple_mapping
---------------------
This is a helper function to make storage setup easier - it helps you to:

* create a simple setup that uses 3 storage backends internally for these
  parts of the namespace:

  - content
  - trash
  - userprofiles
* to configure ACLs protecting these parts of the namespace
* to setup a router middleware that dispatches to these parts of the namespace
* to setup a indexing mixin that maintains an index

Call it like::

    from MoinMoin.storage.backends import create_simple_mapping

    namespace_mapping, router_index_uri = create_simple_mapping(
        backend_uri=...,
        content_acl=dict(before=...,
                         default=...,
                         after=...,
                         hierarchic=..., ),
        user_profile_acl=dict(before=...,
                              default=...,
                              after=..., ),
    )

The `backend_uri` depends on the kind of storage backend you want to use (see
below). Usually it is a URL-like string that looks like::

    fs2:/srv/mywiki/%(nsname)s
    
`fs2` is the name of the backend, followed by a colon, followed by a backend
specific part that may include a `%(nsname)s` placeholder which gets replaced
by 'content', 'trash' or 'userprofiles' for the respective backend.

In this case, the mapping created will look like this:

+----------------+-----------------------------+
| Namespace part | Filesystem path for storage |
+----------------+-----------------------------+
| /              | /srv/mywiki/content/        |
+----------------+-----------------------------+
| /Trash/        | /srv/mywiki/trash/          |
+----------------+-----------------------------+
| /UserProfiles/ | /srv/mywiki/userprofiles/   |
+----------------+-----------------------------+

`content_acl` is a dictionary specifying the ACLs for this part of the
namespace (the normal content). See the docs about ACLs.

acl middleware
--------------
Features:

* protects access to lower storage layers by Access Control Lists
* makes sure there won't be ACL security issues, even if upper layers have bugs
* if you use create_simple_mapping, you just give the ACL parameters, the
  middleware will be set up automatically by moin.

router middleware
-----------------
Features:

* dispatches storage access to different backends depending on the item name
* in POSIX terms: something fstab/mount-like
* if you use create_simple_mapping, the router middleware will be set up
  automatically by moin.

indexing mixin
--------------
Features:

* maintains an index for important metadata values
* speeds up looking up / selecting items
* makes it possible that lower storage layers can be simpler
* if you use create_simple_mapping, the indexing will be set up automatically
  by moin.

fs2 backend
-----------
Features:

* stores into the filesystem
* store metadata and data into separate files/directories
* uses content-hash addressing for revision data files

  - this automatically de-duplicates revision data with same content within the
    whole backend!

Configuration::

    from MoinMoin.storage.backends import create_simple_mapping

    data_dir = '/srv/mywiki/data'
    namespace_mapping, router_index_uri = create_simple_mapping(
        backend_uri='fs2:%s/%%(nsname)s' % data_dir,
        content_acl=dict(before=u'WikiAdmin:read,write,create,destroy',
                         default=u'All:read,write,create',
                         after=u'', ),
        user_profile_acl=dict(before=u'WikiAdmin:read,write,create,destroy',
                              default=u'',
                              after=u'', ),
    )


fs backend
----------
Features:

* stores into the filesystem
* stores meta and data of a revision into single file

`backend_uri` for `create_simple_mapping` looks like::

    fs:/srv/mywiki/data/%(nsname)s

hg backend
----------
Features:

* stores data into Mercurial DVCS (hg) - you need to have Mercurial installed

`backend_uri` for `create_simple_mapping` looks like::

    hg:/srv/mywiki/data/%(nsname)s

sqla backend
------------
Features:

* stores data into a (SQL) database
* uses slqalchemy ORM as database abstraction
* supports multiple types of databases, like:
 
  - sqlite (default, comes built-into Python)
  - postgresql
  - mysql
  - and others (see sqlalchemy docs).

`backend_uri` for `create_simple_mapping` looks like e.g.::

    sqla:sqlite:////srv/mywiki/data/mywiki_%(nsname)s.db
    sqla:mysql://myuser:mypassword@localhost/mywiki_%(nsname)s
    sqla:postgres://myuser:mypassword@localhost/mywiki_%(nsname)s

Please see the sqlalchemy docs about the part after `sqla:`.

In case you use some DBMS (like postgresql or mysql) that does not allow
creation of new databases on an as-needed basis, you need to create the
databases 'mywiki_content', 'mywiki_trash', 'mywiki_userprofiles' yourself
manually.

Grant 'myuser' (his password: 'mypassword') full access to these databases.

.. todo::

   The sqla backend needs more love, more tuning.

fileserver backend
------------------
Features:

* exposes a part of the filesystem as read-only wiki items

  + files will show up as wiki items

    - with 1 revision
    - with as much metadata as can be made up from the filesystem metadata
  + directories will show up as index items, listing links to their contents
* might be useful together with SMBMount pseudo-authenticator

flatfile backend
----------------
Features:

* uses flat files for item storage
* no revisioning
* no separate metadata, just some stuff at top of the (text) data
* thus, only suitable for text items

memory backend
--------------
Features:

* keeps everything in RAM
* definitely not for production use
* mostly intended for testing
* if your system or the moin process crashes, you'll lose everything
* single process only
* maybe not threadsafe

fs19 backend
------------
Features:

* reads moin 1.9 content and users from the filesystem
* read-only, only provided for data migration from moin 1.9.x
* not optimized for speed or resource usage

For more details please see the chapter about upgrading from moin 1.9.


.. todo:

   add more backends / more configuration examples


Mail configuration
==================

Sending E-Mail
--------------
Moin can optionally send E-Mail, e.g. to:

* send out item change notifications.
* enable users to reset forgotten passwords

You need to configure some stuff before sending E-Mail can be supported::

    # the "from:" address [Unicode]
    mail_from = u"wiki <wiki@example.org>"

    # a) using a SMTP server, e.g. "mail.provider.com" (None to disable mail)
    mail_smarthost = "smtp.example.org"

    # if you need to use SMTP AUTH at your mail_smarthost:
    #mail_login = "smtp_username smtp_password"

    # b) alternatively to using SMTP, you can use the sendmail commandline tool:
    #mail_sendmail = "/usr/sbin/sendmail -t -i"

.. todo::

   mail_login is a bit ugly mixing username and password into one string


.. todo::

   describe more moin configuration


=======================
Framework Configuration
=======================

Some stuff you may want to configure for Flask and its extensions (see
their docs for details)::

 # for Flask
 SECRET_KEY = 'you need to change this so it is really secret'
 DEBUG = False # use True for development only, not for public sites!
 #TESTING = False
 #SESSION_COOKIE_NAME = 'session'
 #PERMANENT_SESSION_LIFETIME = timedelta(days=31)
 #USE_X_SENDFILE = False
 #LOGGER_NAME = 'MoinMoin'
 
 # for Flask-Cache:
 #CACHE_TYPE = 'filesystem'
 #CACHE_DIR = '/path/to/flask-cache-dir'


=====================
Logging configuration
=====================

By default, logging is configured to emit output on `stderr`. This will work
OK for the builtin server (will just show on the console) or for e.g. Apache2
(will be put into error.log).

Logging is very configurable and flexible due to the use of the `logging`
module of the Python standard library.

The configuration file format is described there:

http://www.python.org/doc/current/library/logging.html#configuring-logging


There are also some logging configurations in the
`docs/examples/config/logging/` directory.

Logging configuration needs to be done very early, usually it will be done
from your adaptor script (e.g. moin.wsgi)::

    from MoinMoin import log
    log.load_config('wiki/config/logging/logfile')

You have to fix that path to use a logging configuration matching your
needs.

Please note that the logging configuration has to be a separate file (don't
try this in your wiki configuration file)!

