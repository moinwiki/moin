========================================
Introduction into MoinMoin Configuration
========================================
Kinds of configuration files
============================
To change how moinmoin behaves and looks, you may customize it by editing
its configuration files:

* Wiki Engine Configuration

  - the file is often called wikiconfig.py, but it can have any name
  - in that file, there is a Config class; this is the wiki engine's configuration
  - it is written in Python

* Framework Configuration

  - this is also located in the same file as the Wiki Engine Configuration
  - there are some UPPERCASE settings at the bottom; this is the framework's
    config (for Flask and Flask extensions)
  - it is written in Python

* Logging Configuration

  - optional; if you don't configure this, it will use the builtin defaults
  - this is a separate file, often called logging.conf
  - it has an .ini-like file format

Do small steps and have backups
-------------------------------
Start from one of the sample configs provided with moin
and only perform small changes, then try it before testing the next change.

If you're not used to the config file format, backup your last working config
so you can revert to it in case you make some hard to find typo or other error.

Editing Python files
--------------------
When editing Python files, be careful with indentation, only use multiples of
4 spaces to indent, and no tabs!

Also, be careful with syntax in general, it must be valid Python code or else
it will crash with some error when trying to load the config. If that happens,
read the error message, it will usually tell the line number and what the problem
is. If you can't fix it easily, then revert to your backup of your last working
config.

Why use Python for configuration?
---------------------------------
At first, you might wonder why we use Python code for configuration. One of the
reasons is that it is a powerful language. MoinMoin itself is developed in Python
and using something else would usually mean much more work when developing new
functionality.

Directory Structure
===================

Shown below are parts of the directory structure after cloning moin and running quickinstall.py.
The default uses the OS file system for storage of wiki data and indexes.
The directories and files shown are referenced in this section of documentation related to configuration::

    moin/                     # clone root, default name
        contrib/              # scripts and docs of interest to developers
        docs/                 # moin documentation in restructured text (.rst) format
            _build/
                html/         # local copy of moin documentation, created by running "./m docs" command
        requirements.d/       # package requirements used by quickinstall.py
        scripts/              # misc. scripts of interest to developers
        src/
            moin/             # large directory containing moin application code
        wiki/                 # the wiki instance; created by running "./m new-wiki" or "moin create-instance" commands
            data/             # wiki data and metadata
            index/            # wiki indexes
        wiki_local/           # a convenient location to store custom CSS, Javascript, templates, logos, etc.
        wikiconfig.py         # main configuration file, modify this to add or change features
        intermap.txt          # interwiki map: copied by quickinstall.py, updated by "./m interwiki"

After installing moin from pypi or unpacking using a package manager, the directory structure will
look like this::

    myvenv/                 # virtualenv root
        bin/                # Windows calls this directory Scripts
        include             # Windows calls this directory Include
        lib/                # Windows calls this directory Lib, includes moin package

After activating the above venv, `moin create-instance -p <mywiki>` creates the structure below. Multiple
instances of `mywiki` can be created with different names. `mywiki` may be created as a
subdirectory of `myvenv` or elsewhere. The `preview` and `sql` subdirectories are created when a
user edits a wiki item. To run moin using the built-in server, cd to the `<mywiki>` directory
and execute `moin run`.::

    mywiki/                 # wikiconfig dir, use this as CWD for moin commands
        wiki/               # the wiki instance; created by `moin create-instance`
            data/           # wiki data and metadata
            index/          # wiki indexes
            preview/        # text item backups are created when user clicks edit Preview button
            sql/            # sqlite database used for edit locking
        wiki-local/         # store custom CSS, Javascript, templates, logos, etc. here
        wikiconfig.py       # main configuration file, modify this to add or change features
        intermap.txt        # list of external wikis used in wikilinks: [[MeatBall:InterWiki]]

wikiconfig.py Layout
====================

A wikiconfig.py looks like this::

 # -*- coding: utf-8 -*-
 from moin.config.default import DefaultConfig

 class Config(DefaultConfig):
     # some comment
     sometext = 'your value'
     somelist = [1, 2, 3]

 MOINCFG = Config  # Flask only likes uppercase characters
 SOMETHING_FLASKY = 'foobar'

Let's go through this line-by-line:

0. this declares the encoding of the config file; make sure your editor uses
   the same encoding (character set), especially if you intend to use non-ASCII
   characters.
1. this gets the DefaultConfig class from the moin code; it has default
   values for all settings and this will save you work, because you only have to define
   the parts that should be different from the defaults.
2. empty line, for better readability
3. define a new class `Config` that inherits most content from
   `DefaultConfig`; this is the wiki engine configuration and if you define some
   setting within this class, it will overwrite the setting from DefaultConfig.
4. a `#` character defines a comment in your config. This line, as
   well as all other following lines with Config settings, is indented by 4
   blanks, because Python defines blocks by indentation.
5. define a Config attribute called `sometext` with value 'your value'.
6. define a Config attribute called `somelist` with value [1, 2, 3]; this is
   a list with the numbers 1, 2 and 3 as its elements.
7. empty line, for better readability
8. the special line "MOINCFG = Config" must stay there in exactly this form for
   technical reasons.
9. UPPERCASE code at the bottom, outside the Config class is a framework
   configuration; usually something for Flask or some Flask extension.

A real-life example of a `wikiconfig.py` can be found in the
`src/moin/config` directory. This file will be initially copied to your
wiki path when you create a new wiki and `wikiconfig.py` is missing.

=========================
Wiki Engine Configuration
=========================

User Interface Customization
============================

Customizing a wiki usually requires adding a few files that contain custom templates,
logo image, CSS, etc. To accomplish this, a directory named "wiki_local"
is provided. One advantage of using this directory and following the examples below
is that MoinMoin will serve the files.

If desired, the name of this directory may be changed or a separate subdirectory
for template files may be created by editing
the wikiconfig file and changing the line that defines `template_dirs`::

    template_dirs = [os.path.join(wikiconfig_dir, 'wiki_local'), ]

Using a custom snippets.html template
-------------------------------------
The user interface or html elements that often need customization are
defined as macros in the template file `snippets.html`.

If you would like to customize some parts, you have to copy the built-in
`src/moin/templates/snippets.html` file and save it in the `wiki_local` directory so moin
can use your copy instead of the built-in one.

To customize something, you usually have to insert your code between the
`{% macro ... %}` and `{% endmacro %}` lines, see below for more details.

Logo
~~~~
To replace the default MoinMoin logo with your own logo, copy your logo to
`wiki_local` and change the logo macro to something like::

    {% macro logo() -%}
        <img src="{{ url_for('serve.files', name='wiki_local', filename='MyLogo.png') }}" id="moin-img-logo" alt="Logo">
    {%- endmacro %}

This is recommended to allow your users to immediately recognize which wiki site they are currently on.

You can use text or even nothing at all for the logo, it is not
required to be an image::

    {% macro logo() -%}
        <span style="font-size: 50px; color: red;">My Wiki</span>
    {%- endmacro %}

Make sure the dimensions of your logo image or text fit into the layout of
the theme(s) your wiki users are using.

Displaying license information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you need to display something like license information for your content or
some other legalese, use this macro::

    {# License information in the footer #}
    {% macro license_info() -%}
    All wiki content is licensed under the WTFPL.
    {%- endmacro %}

Inserting pieces of HTML
~~~~~~~~~~~~~~~~~~~~~~~~
At some specific places, you can add a piece of your own html into the
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
At the bottom of your wiki pages, usually some text and image links are shown
pointing out that the wiki runs MoinMoin, uses Python, that MoinMoin is GPL licensed, etc.

If you run a public site using MoinMoin, we would appreciate if you
*keep* those links, especially the "MoinMoin powered" one.

However, if you can't do that for some reason, feel free to modify these
macros to show something else::

    {# Image links in the footer #}
    {% macro creditlogos(start='<ul id="moin-creditlogos"><li>'|safe, end='</li></ul>'|safe, sep='</li><li>'|safe) %}
    {{ start }}
    {{ creditlogo('https://moinmo.in/', url_for('.static', filename='logos/moinmoin_powered.png'),
       'MoinMoin powered', 'This site uses the MoinMoin Wiki software.') }}
    {{ sep }}
    {{ creditlogo('https://moinmo.in/Python', url_for('.static', filename='logos/python_powered.png'),
       'Python powered', 'MoinMoin is written in Python.') }}
    {{ end }}
    {% endmacro %}

    {# Text links in the footer #}
    {% macro credits(start='<p id="moin-credits">'|safe, end='</p>'|safe, sep='<span>&bull;</span>'|safe) %}
    {{ start }}
    {{ credit('https://moinmo.in/', 'MoinMoin Powered', 'This site uses the MoinMoin Wiki software.') }}
    {{ sep }}
    {{ credit('https://moinmo.in/Python', 'Python Powered', 'MoinMoin is written in Python.') }}
    {{ sep }}
    {{ credit('https://moinmo.in/GPL', 'GPL licensed', 'MoinMoin is GPL licensed.') }}
    {{ sep }}
    {{ credit('https://validator.w3.org/check?uri=referer', 'Valid HTML 5', 'Click here to validate this page.') }}
    {{ end }}
    {% endmacro %}

Adding scripts
~~~~~~~~~~~~~~
You can add scripts like this::

    {# Additional Javascript #}
    {% macro scripts() -%}
    <script type="text/javascript" src="{{ url_for('serve.files', name='wiki_local', filename='MyScript.js') }}"></script>
    {% endmacro %}

Adding CSS
~~~~~~~~~~
To apply some style changes, add some custom css and overwrite any style you
don't like in the base theme::

    {# Additional Stylesheets (after theme css, before user css #}
    {% macro stylesheets() -%}
        <link media="screen" href="{{ url_for('serve.files', name='wiki_local', filename='company.css') }}" title="Company CSS" rel="stylesheet" />
        <link media="screen" href="{{ url_for('serve.files', name='wiki_local', filename='red.css') }}" title="Red Style" rel="alternate stylesheet" />
        <link media="screen" href="{{ url_for('serve.files', name='wiki_local', filename='green.css') }}" title="Green Style" rel="alternate stylesheet" />
    {%- endmacro %}

You can either add some normal css stylesheet or add a choice of alternate
stylesheets.

See:

* `CSS media types <https://www.w3.org/TR/CSS2/media.html>`_
* `Alternate Stylesheets <https://alistapart.com/article/alternate/>`_

A good way to test a stylesheet is to first use it as user CSS before
configuring it for the public.

Please note that `stylesheets` will be included no matter what theme the
user has selected, so either only apply changes to all available themes or
force all users to use the same theme, so that your CSS displays correctly.

Customize the CMS Theme
~~~~~~~~~~~~~~~~~~~~~~~
Moin provides one CMS theme: the Topside CMS Theme.

The CMS theme replaces the wiki navigation links used by editors and
administrators with a few links to the most important items within your wiki. Wiki
admins may want to make the CMS theme the default theme when:

 - Casual visitors are interested in viewing the wiki content, but confused by the wiki navigation links.
 - Errant bots are overloading your server by following the wiki navigation links on every page.
 - Contributors do not mind logging in before editing.

Customizing the CMS header may be done as follows. Several restarts of the server may be required:

 - Copy /templates/snippets.html to the wiki_local directory and find the `macro cms_header`.
 - Usually the logo, sitename, and search form sections are not changed.
 - If a link to login is wanted, leave the "request.user_agent" section as is, else remove the entire block.
 - Add or remove links in the navibar section as required, defaults links include Home page
   and Global Index.
 - If many links are desired, consider using `macro custom_panels`.
 - Test by logging in and setting "Topside CMS Theme" as your preferred theme.
 - After testing, make the cms theme the default theme by adding ``theme_default = "topside_cms"`` to wikiconfig.
 - Inform your editors to login and set another theme as their preferred theme.
 - If the login link was removed, the login page is available by keying ``+login`` as the page name in the browser URL.

Here is the source code segment from snippets.html::

    {# Header/Sidebar for topside_cms theme - see docs for tips on customization #}
    {% macro cms_header() %}
        <header id="moin-header" lang="{{ theme_supp.user_lang }}" dir="{{ theme_supp.user_dir }}">
            {% block header %}

                {% if logo() %}
                    <div id="moin-logo">
                        <a href="{{ url_for('frontend.show_item', item_name=cfg.root_mapping.get('', cfg.default_root)) }}">
                            {{ logo() }}
                        </a>
                    </div>
                {%- endif %}

                {% if cfg.sitename %}
                    <a class="moin-sitename" href="{{ url_for('frontend.show_item', item_name=cfg.root_mapping.get('', cfg.default_root)) }}">
                        {{ cfg.sitename }}
                    </a>
                    <br>
                {%- endif %}

                {% if request.user_agent and search_form %} {# request.user_agent is true if browser, false if run as moin dump-html #}
                    {{ utils.header_search(search_form) }}
                {% endif %}

                {% if request.user_agent %} {# request.user_agent is true if browser, false if run as moin dump-html #}
                    <ul id="moin-username" class="moin-header-links">
                        {{ utils.user_login_logoff() }}
                    </ul>
                {%- endif %}

                <ul id="moin-navibar" class="moin-header-links panel">
                    {# wiki admins should add links and headings for key items within the local wiki below #}
                    <li class="moin-panel-heading">Navigation</li>
                    <li class="wikilink"><a href="{{ url_for('frontend.show_item', item_name='Home') }}">Start</a></li>
                    <li class="wikilink"><a href="{{ url_for('frontend.show_item', item_name='+index') }}">Index</a></li>
                </ul>

                {{ custom_panels() }}

            {% endblock %}
        </header>
        <br>
    {% endmacro %}

Displaying user avatars
-----------------------
Optionally, moin can display avatar images for the users, using gravatar.com
service. To enable it, add or uncomment this line in wikiconfig::

    user_use_gravatar = True

Please note that using the gravatar service has some privacy issues:

* to register your image for your email at gravatar.com, you need to give them
  your email address, which is the same as you use in your wiki user profile.
* when the wiki displays an avatar image on some item / view, the URL will be
  exposed as referrer to the avatar service provider, so they will roughly
  know which people read or work on which wiki items / views.

XStatic Packages
----------------
`XStatic <https://readthedocs.org/projects/xstatic>`_ is a packaging standard
to package external static files as a Python package, often third party.
That way they are easily usable on all operating systems, whether it has a package management
system or not.

In many cases, those external static files are maintained by someone else (like jQuery
javascript library or larger js libraries) and we definitely do not want to merge
them into our project.

For MoinMoin we require the following XStatic Packages in pyproject.toml:

* `jquery <https://pypi.org/project/XStatic-jQuery>`_
  for jquery lib functions loaded in the template file base.html

* `jquery_file_upload <https://pypi.org/project/XStatic-jQuery-File-Upload>`_
  loaded in the template file of index view. It allows to upload many files at once.

* `bootstrap <https://pypi.org/project/XStatic-Bootstrap>`_
  used by the basic theme.

* `font_awesome <https://pypi.org/project/XStatic-Font-Awesome>`_
  provides text icons.

* `ckeditor <https://pypi.org/project/XStatic-CKEditor>`_
  used in template file modify_text_html. A WYSIWYG editor similar to word processing
  desktop editing applications.

* `autosize <https://pypi.org/project/XStatic-autosize>`_
  used by basic theme to adjust textarea on modify view.

* `svgedit_moin <https://pypi.org/project/XStatic-svg-edit-moin>`_
  is loaded at template modify_svg-edit. It is a fast, web-based, Javascript-driven
  SVG editor.

* `jquery_tablesorter <https://pypi.org/project/XStatic-JQuery.TableSorter/2.14.5.1>`_
  used to provide client side table sorting.

* `pygments <https://pypi.org/project/XStatic-Pygments>`_
  used to style code fragments.


These packages are imported in wikiconfig by::

    from xstatic.main import XStatic
    # names below must be package names
    mod_names = [
        'jquery', 'jquery_file_upload',
        'bootstrap',
        'font_awesome',
        'ckeditor',
        'autosize',
        'svgedit_moin',
        'jquery_tablesorter',
        'pygments',
    ]
    pkg = __import__('xstatic.pkg', fromlist=mod_names)
    for mod_name in mod_names:
        mod = getattr(pkg, mod_name)
        xs = XStatic(mod, root_url='/static', provider='local', protocol='http')
        serve_files[xs.name] = xs.base_dir

In a template file you access the files of such a package by its module name::

    url_for('serve.files', name='the mod name', filename='the file to load')

Adding XStatic Packages
-----------------------

The following example shows how you can enable the additional package
`XStatic-MathJax <https://pypi.org/project/XStatic-MathJax>`_ which is
used for mathml or latex formulas in an item's content.

* install xstatic-mathjax (e.g. using ``pip install xstatic-mathjax``)
* add the name 'mathjax' to to the list of mod_names in wikiconfig
* copy /templates/snippets.html to the wiki_local directory
* modify the snippets.html copy by adding the required fragment to the scripts macro::

    {% macro scripts() -%}
    <script type="text/x-mathjax-config">
    MathJax.Hub.Config({
        extensions: ["tex2jax.js"],
        jax: ["input/TeX","output/HTML-CSS"],
        tex2jax: {inlineMath: [["$","$"],["\\(","\\)"]]}
    });
    </script>
    <script src="{{ url_for('serve.files', name='mathjax', filename='MathJax.js') }}"></script>
    {%- endmacro %}

Custom Themes
-------------
In case you want to do major changes to how MoinMoin displays its pages, you
could also write your own theme.

Caution: developing your own theme means you also have to maintain and update it,
which normally requires a long-term effort.

To add a new theme, add a new directory under src/moin/themes/ where the directory
name is the name of your theme. Note the directory structure under the other existing
themes. Copy an `info.json` file to your theme directory and edit as needed.
Create a file named theme.css in the src/moin/themes/<theme name>/static/css/ directory.

To change the layout of the theme header, sidebar and footer, create a templates/ directory and
copy and modify the files layout.html and show.html from either src/moin/templates/ or one
of the existing theme templates directories.

For many themes, modifying the files noted above will be sufficient. If changes to
views are required, copy additional template files. If there is a requirement to change
the MoinMoin base code, please consider submitting a patch.

Authentication
==============
MoinMoin uses a configurable `auth` list of authenticators, so the admin can
configure whatever he/she likes to allow for authentication. Moin processes this
list from left to right.

Each authenticator is an instance of some specific class, configuration of
the authenticators usually works by giving them keyword arguments. Most have
reasonable defaults though.

MoinAuth
--------
This is the default authentication moin uses if you don't configure something
else. The user logs in by filling out the login form with username and
password, moin compares the password hash against the one stored in the user's
profile and if both match, the user is authenticated::

    from moin.auth import MoinAuth
    auth = [MoinAuth()]  # this is the default!

HTTPAuthMoin
------------
With HTTPAuthMoin moin does http basic authentication by itself without the help of
the web server::

    from moin.auth.http import HTTPAuthMoin
    auth = [HTTPAuthMoin(autocreate=True)]

If configured like that, moin will request authentication by emitting a
http header. Browsers then usually show some login dialogue to the user,
asking for username and password. Both then gets transmitted to moin and it
is compared against the password hash stored in the user's profile.

**Note:** when HTTPAuthMoin is used, the browser will show that login dialogue, so
users must login to use the wiki.

GivenAuth
---------
With GivenAuth moin relies on the webserver doing the authentication and giving
the result to moin, usually via the environment variable REMOTE_USER::

    from moin.auth import GivenAuth
    auth = [GivenAuth(autocreate=True, coding='utf-8')]

Using this method has some pros and cons:

* you can use lots of authentication extensions available for your web server
* but the only information moin will get via REMOTE_USER is the authenticated
  user's name, nothing else. So, e.g. for LDAP/AD, you won't get additional
  content stored in the LDAP directory.
* everything you won't get, but which you need, will need to be manually stored
  and updated in the user's profile, e.g. the user's email address, etc.

Please note that you must give the correct character set so that moin
can decode the username to unicode, if necessary. For environment variables
like REMOTE_USER, the coding might depend on your operating system.

If you do not know the correct coding, try: 'utf-8', 'iso-8859-1', ...

.. todo::

   add the usual coding(s) for some platforms (like windows)

To try it out, change configuration, restart moin and then use some non-ASCII
username (like with german umlauts or accented characters). If moin does not
crash (log a Unicode Error), you have likely found the correct coding.

For users configuring GivenAuth on Apache, an example virtual host configuration
is included at `contrib/deployment/moin-http-basic-auth.conf`


LDAPAuth
--------
With LDAPAuth you can authenticate users against a LDAP directory or MS Active Directory service.

LDAPAuth with single LDAP server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This example shows how to use LDAPAuth with a single LDAP/AD server::

    from moin.auth.ldap_login import LDAPAuth
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
This example shows how to use LDAPAuth with a two LDAP/AD servers, such as in a setup
with a primary controller and backup domain controller::

    # ... same as for single server (except the line with "auth =") ...
    ldap_authenticator2 = LDAPAuth(
        server_uri='ldap://otherldap',  # ldap / active directory server URI for second server
        name='ldap2',
        **ldap_common_arguments
    )

    auth = [ldap_authenticator1, ldap_authenticator2, ]

AuthLog
-------
AuthLog is not a real authenticator in the sense that it authenticates (logs in) or
deauthenticates (logs out) users. It is passively logging informations for
authentication debugging::

    from moin.auth import MoinAuth
    from moin.auth.log import AuthLog
    auth = [MoinAuth(), AuthLog(), ]

Example logging output::

 2011-02-05 16:35:00,229 INFO MoinMoin.auth.log:22 login: user_obj=<moin.user.User at 0x90a0f0c name:'ThomasWaldmann' valid:1> kw={'username': 'ThomasWaldmann', 'attended': True, 'multistage': None, 'login_password': 'secret', 'login_username': 'ThomasWaldmann', 'password': 'secret', 'login_submit': ''}
 2011-02-05 16:35:04,716 INFO MoinMoin.auth.log:22 session: user_obj=<MoinMoin.user.User at 0x90a0f6c name:'ThomasWaldmann' valid:1> kw={}
 2011-02-05 16:35:06,294 INFO MoinMoin.auth.log:22 logout: user_obj=<MoinMoin.user.User at 0x92b5d4c name:'ThomasWaldmann' valid:False> kw={}
 2011-02-05 16:35:06,328 INFO MoinMoin.auth.log:22 session: user_obj=None kw={}

**Note:** there is sensitive information like usernames and passwords in this
log output. Make sure you only use this for testing only and delete the logs when
done.

SMBMount
--------
SMBMount is no real authenticator in the sense that it authenticates (logs in)
or deauthenticates (logs out) users. It instead catches the username and password
and uses them to mount a SMB share as this user.

SMBMount is only useful for very special applications, e.g. in combination
with the fileserver storage backend::

    from moin.auth.smb_mount import SMBMount

    smbmounter = SMBMount(
        # you may remove default values if you are happy with them
        # see man mount.cifs for details
        server='smb.example.org',  # (no default) mount.cifs //server/share
        share='FILESHARE',  # (no default) mount.cifs //server/share
        mountpoint_fn=lambda username: '/mnt/wiki/%s' % username,  # (no default) function of username to determine the mountpoint
        dir_user='www-data',  # (no default) username to get the uid that is used for mount.cifs -o uid=...
        domain='DOMAIN',  # (no default) mount.cifs -o domain=...
        dir_mode='0700',  # (default) mount.cifs -o dir_mode=...
        file_mode='0600',  # (default) mount.cifs -o file_mode=...
        iocharset='utf-8',  # (default) mount.cifs -o iocharset=... (try 'iso8859-1' if default does not work)
        coding='utf-8',  # (default) encoding used for username/password/cmdline (try 'iso8859-1' if default does not work)
        log='/dev/null',  # (default) logfile for mount.cifs output
    )

    auth = [....., smbmounter]  # you need a real auth object in the list before smbmounter

    smb_display_prefix = "S:"  # where //server/share is usually mounted for your windows users (display purposes only)

.. todo::

   check if SMBMount still works as documented


Transmission security
=====================
Credentials
-----------
Some of the authentication methods described above will transmit credentials,
like usernames and password, in unencrypted form:

* MoinAuth: when the login form contents are transmitted to moin, they contain
  username and password in clear text.
* HTTPAuthMoin: your browser will transfer username and password in a encoded
  (but NOT encrypted) form with EVERY request; it uses http basic auth.
* GivenAuth: check the potential security issues of the authentication
  method used by your web server; for http basic auth please see HTTPAuthMoin.

Contents
--------
http transmits everything in clear text and is therefore not encrypted.

Encryption
----------
Transmitting unencrypted credentials or contents can cause serious issues in many
scenarios.

We recommend you make sure the connections are encrypted, like with https or VPN
or an ssh tunnel.

For public wikis with very low security / privacy needs, it might not be needed
to encrypt the content transmissions, but there is still an issue for the
credential transmissions.

When using unencrypted connections, wiki users are advised to make sure they
use unique credentials and not reuse passwords that are used for other purposes.


Password security
=================
Password strength
-----------------
As you might know, many users are bad at choosing reasonable passwords and some
are tempted to use easily crackable passwords.

To help users choose reasonable passwords, moin has a simple builtin
password checker that is enabled by default and does some sanity checks,
so users don't choose easily crackable passwords.

It **does** check:

* length of password (default minimum: 8)
* amount of different characters in password (default minimum: 5)
* password does not contain user name
* user name does not contain password
* password is not a keyboard sequence (like "ASDFghjkl" or "987654321"),
  currently we have only US and DE keyboard data built-in.

It **does not** check:

* whether the password is in a well-known dictionary or password list
* whether a password cracker can break it

If you are not satisfied with the default values, you can easily customize the
checker::

    from moin.config.default import DefaultConfig, _default_password_checker
    password_checker = lambda cfg, name, pw: _default_password_checker(
                           cfg, name, pw, min_length=10, min_different=6)

You could also completely replace it with your own implementation.

If your site has rather low security requirements, you can disable the checker
by::

    password_checker = None  # no password checking


Password storage
----------------
Moin never stores wiki user passwords in clear text, but uses strong
cryptographic hashes provided by the "passlib" library, see there for details:

    https://passlib.readthedocs.io/en/stable/


The passlib docs recommend 3 hashing schemes that have good security:
sha512_crypt, pbkdf2_sha512 and bcrypt (bcrypt has additional binary/compiled
package requirements, please refer to the passlib docs in case you want to use
it).

By default, we use sha512_crypt hashes with default parameters as provided
by passlib (this is same algorithm as moin >= 1.9.7 used by default).

In case you experience slow logins or feel that you might need to tweak the
hash generation for other reasons, please read the passlib docs. moin allows
you to configure passlib's CryptContext params within the wiki config, the
default is this:

::

    passlib_crypt_context = dict(
        schemes=["sha512_crypt", ],
    )


Authorization
=============
Moin uses Access Control Lists (ACLs) to specify who is authorized to perform
a given action. ACLs enable wiki administrators and possibly users to choose
between *soft security* and *hard security*.

* if your wiki is rather open (soft security), you make it easy to contribute, e.g. a
  user who is not a regular user of your wiki could fix some typos he has just
  found. However, a hostile user or bot could easily add spam into your wiki.
  In this case, an active user community can quickly detect and remove the spam.
* if your wiki is rather closed (hard security), e.g. you require every user to first apply for an
  account and to log in before being able to do changes, you will rarely get
  contributions from casual users and possibly discourage contributions from
  members of your community. But, getting spam is then less likely.
* ACLs provide the means of using both methods. Key wiki items that are frequently viewed
  and infrequently changed may be updated only by selected users while other items that
  are frequently changed may be updated by any user.

Moin's default configuration makes use of *hard security* to prevent unwanted spam.
Wiki administrators may soften security by reconfiguring the default ACLs.

As wiki items are created and updated, the default configuration may be overridden
on specific items by setting an ACL on that item.

Hardening security implies that there will be a registration and login process that enables
individual users to gain privileges. While wikis with a small user community may function
with ACLs specifying only usernames, larger wikis will make use of ACLs that reference
groups or lists of usernames. The definitions of built-in groups and creation of groups are
discussed below under the headings `ACLs - special groups` and `Groups`.


ACL for functions
-----------------
Moin has some built in functions that are protected by ACLs:

* superuser - used for miscellaneous administrative functions. Give this only to
  highly trusted people

Example::

    acl_functions = 'YourName:superuser'

ACLs for contents
-----------------
This type of ACL controls access to content stored in the wiki. Wiki items
may have ACLs defined in their metadata. Within wikiconfig, ACLs are specified
per namespace and storage backend (see storage backend docs for details). The
example below shows an entry for the default namespace::

    default_acl=dict(before='SuperUser:read,write,create,destroy,admin',
                     default='TrustedEditorGroup:read,write,create,destroy,admin Known:read,write,create',
                     after='All:read',
                     hierarchic=False, ),

As shown above, `before`, `default` and  `after` ACLs are specified. The `default` ACL
is only used if no ACL is specified in the metadata of the target item.

.. digraph:: acl_order

   rankdir=LR;
   "before" -> "item acl from metadata (if specified)" -> "after";
   "before" -> "default (otherwise)"                   -> "after";

How to use before, default, and after:

* `before` is usually used to force something, for example if you want to give some
  wiki admin all permissions indiscriminately; in the example above, no one can create an item
  ACL rule locking out SuperUser's access
* `default` is the behavior if no ACL was created in the item's metadata; above, only members of a trusted group can write ACL rules or delete items, and a user must be logged in (known) to write or create items
* `after` is rarely used and when it is, it is used to "not forget something unless otherwise specified";
  above, all users may read all items unless blocked (or given more privileges) by an ACL on the target item

When configuring content ACLs, you can choose between standard (flat) ACL
processing and hierarchic ACL processing. Hierarchic processing means that
subitems inherit ACLs from their parent items if they don't have an ACL themselves.

Note that while hierarchic ACLs are rather convenient sometimes, they make the
system more complex. You have to be very careful with permission
changes happening as a result of changes in the hierarchy, such as when you create,
rename or delete items. When multiple item names are used the complexity increases
even more because all parents are searched for ACLs -- if conflicting
allow/deny ACLs are found allow always wins.

Supported capabilities (rights):

* read - read content
* write - write (edit, modify, delete) content
* create - create new items
* destroy - completely destroy revisions or items; to be given only to *fully-trusted* users
* admin - change (create, remove) ACLs for the item; to be given only to *fully-trusted* users

The write capability includes the authority to delete an item since any user with write authority
may edit and remove or replace all content. A deleted item does not appear in the Global Index,
but the deletion event does appear in the global history. To recover a deleted item, find the
deleted item line in global history, click the link to the item's history, and then click a revert
link to one of the prior revisions.

ACLs - special groups
---------------------
In addition to the groups provided by the group backend(s), there are some
special group names available within ACLs. These names are case-sensitive
and must be capitalized as shown:

* All - a virtual group containing every user, including users who have not logged in
* Known - a virtual group containing every logged-in user
* Trusted - a virtual group containing every logged-in user who was logged
  in by some specific "trusted" authentication method other than the default MoinAuth.


ACLs - basic syntax
-------------------
An ACL is a unicode string with one or more access control entries
which are space separated.

An entry is a colon-separated set of two values:

* the left side is a comma-separated list of user and/or group names
* the right side is a comma-separated list of rights / capabilities for those users/groups.

An ACL is processed from left to right, where the first left-side match counts.

Example::

    "SuperMan,WonderWoman:read,write,create,destroy,admin All:read,write"

If "SuperMan" is currently logged in and moin processes this ACL, it will find
a name match in the first entry. If moin wants to know whether he may destroy,
the answer will be "yes", as destroy is one of the capabilities/rights listed
on the right side of this entry.

If "JoeDoe" is currently logged in and moin processes this ACL, the first entry
won't match, so moin will proceed left-to-right and look at the second entry.
Here we have the special group name, "All" (and JoeDoe is obviously a member of
this group), so this entry matches.
If moin wants to know whether he may destroy, the answer will be "no", as
destroy is not listed on the right side of the "All" entry. If moin wants to know
whether he may write, the answer will be "yes".

Notes:

* As a consequence of the left-to-right and first-match-counts processing,
  you must order ACL entries so that the more specific ones (like for
  "SuperMan") are left of the less specific ones.
  Usually, you want this order:

  1) usernames
  2) special groups
  3) more general groups
  4) Trusted
  5) Known
  6) All

* Do not put any spaces into an ACL entry, unless it is part of a user or
  group name.

* A right that is not explicitly given by an applicable ACL is denied.

ACLs - entry prefixes
---------------------
To make the system more flexible, there are two ways to modify an ACL entry: prefixing it with a '+' or a '-'.

If you use one of the two, MoinMoin will search for both a username and permission, and a match will have to match
both the name of user (left-side) *and* the permission MoinMoin is searching for (right-side), otherwise
it will continue with the next entry.

'+' indicates that MoinMoin should give the permission(s) specified on the right side.

'-' indicates that MoinMoin should deny the permission(s) specified on the right side.

Example::

    "+SuperMan:create,destroy,admin -Idiot:write All:read,write"

If "SuperMan" is currently logged in and moin wants to know whether he may
destroy, it'll find a match in the first entry, because the name matches *and* permission
in question matches. As the prefix is '+', the answer is "yes".

If moin wants to know whether SuperMan may write, the first entry will not match
on both sides, so moin will proceed and look at the second entry. It doesn't
match, so it will look at the third entry. Of course "SuperMan" is a member of
group "All", so we have a match here. As "write" is listed on the right side,
the answer will be "yes".

If the rule above did not have a leading + before SuperMan and moin wants to know
whether SuperMan may write, then the left side matches at the first entry and the
answer will be "no" because "write" is not listed on the right side.

If "Idiot" is currently logged in and moin wants to know whether he may write,
it will find no match in the first entry, but the second entry will match. As
the prefix is '-', the answer will be "no". Because a match has been made,
the third entry is not processed.

Notes:

* you usually use these modifiers if most of the rights for a given user shall be specified
  later, but a special user or group should be treated slightly different for
  a few special rights.

ACLs - Default entry
--------------------
There is a special ACL entry, "Default", which expands itself in-place to the
default ACL.

This is useful, for example, if when you mostly want the default ACL, but
with a slight modification, but you don't want to type in the default ACL
all the time and you also want to be able to change the default ACL without
having to edit lots of items.

Example::

    "-NotThisGuy:write Default"

This will behave as usual, except that "NotThisGuy" will never be given write
permission.


Secrets
=======
Moin uses secrets to encrypt or cryptographically sign something like:

* tickets

Secrets are long random strings and *not* a reuse of any of your passwords.
Don't use the strings shown below, they are NOT secret as they are part of the
moin documentation. Make up your own secrets::

    secrets = {
        'security/ticket': 'asdasdvarebtZertbaoihnownbrrergfqe3r',
    }

If you don't configure these secrets, moin will detect this and reuse Flask's
SECRET_KEY for all secrets it needs.


Groups
======

Group names can be used in place of usernames within ACLs.
There are three types of groups: WikiGroups, ConfigGroups, and CompositeGroups.
A group is a list of unicode names, where a name may be either a username or
another group name.

Use of groups will reduce the administrative effort required to maintain ACL rules,
especially in wikis with a large community of users. Rather than change multiple
ACL rules to reflect a new or departing member, a group may be updated. To achieve
maximum benefit, some advance planning is required to determine the kind and names
of groups suitable for your wiki.

The wiki server must be restarted to reflect updates made to ConfigGroups
and CompositeGroups.

Names of WikiGroup items must end in "Group". There is no such requirement for the
names of ConfigGroups or CompositeGroups.

Group backend configuration
---------------------------

The WikiGroups backend is enabled by default so there is no need to add the following to wikiconfig::

    def groups(self):
        from moin.datastructures import WikiGroups
        return WikiGroups()

To create a WikiGroup that can be used in an ACL rule:

* Create a wiki item with a name ending in "Group" (the content of the item is not relevant).
* Edit the metadata and add entries under the heading "Wiki Groups", one entry per line.
* Leading and trailing spaces are ignored, internal spaces are accepted.::

    JaneDoe
    JohnDoe
    SomeOtherGroup

* Use the new group name in one or more ACL rules.
* For public wikis, it is recommended that a TrustedEditorGroup (or similar name) be created.


The ConfigGroups backend uses groups defined in the configuration file. Adding the
following to wikiconfig creates an EditorGroup and an AdminGroup and prevents
the use of any WikiGroups::

    def groups(self):
        from moin.datastructures import ConfigGroups
        groups = {'EditorGroup': ['AdminGroup', 'John', 'JoeDoe', 'Editor1'],
                  'AdminGroup': ['Admin1', 'Admin2', 'John']}
        return ConfigGroups(groups)

CompositeGroups enable both ConfigGroups and WikiGroups to be used. The example
below defines the same ConfigGroups used above and enables the use of WikiGroups.
Note that order matters! Since ConfigGroups backend is first in the return tuple,
the EditGroup and AdminGroup defined below will be used should there be WikiGroup
items with the same names::

    def groups(self):
        from moin.datastructures import ConfigGroups, WikiGroups, CompositeGroups
        groups = {'EditorGroup': ['AdminGroup', 'John', 'JoeDoe', 'Editor1'],
                  'AdminGroup': ['Admin1', 'Admin2', 'John']}
        return CompositeGroups(ConfigGroups(groups), WikiGroups())


Dict backend configuration
--------------------------

The dict backend provides a means for translating phrases in documentation through the
use of the GetVal macro.

The WikiDicts backend is enabled by default so there is no need to add the following to wikiconfig::

    def dicts(self):
        from moin.datastructures import WikiDicts
        return WikiDicts()

To create a WikiDict that can be used in an GetVal macro:

* Create a wiki item with a name ending in "Dict" (the content of the item is not relevant)
* Edit the metadata and add an entry under the heading "Wiki Dict"::

    apple=red
    banana=yellow
    pear=green

The ConfigDicts backend uses dicts defined in the configuration file. Adding the
following to wikiconfig creates a OneDict and a NumbersDict and prevents
the use of any WikiDicts::

    def dicts(self):
        from moin.datastructures import ConfigDicts
        dicts = {'OneDict': {'first_key': 'first item',
                              'second_key': 'second item'},
                 'NumbersDict': {'1': 'One',
                                  '2': 'Two'}}
        return ConfigDicts(dicts)

CompositeDicts enable both ConfigDicts and WikiDicts to be used. The example
below defines the same ConfigDicts used above and enables the use of WikiDicts.
Note that order matters! Since ConfigDicts backend is first in the return tuple,
the OneDict and NumbersDict defined below will be used should there be WikiDict
items with the same names::

    def dicts(self):
        from moin import ConfigDicts, WikiDicts, CompositeDicts
        dicts = {'OneDict': {'first_key': 'first item',
                              'second_key': 'second item'},
                 'NumbersDict': {'1': 'One',
                                  '2': 'Two'}}
        return CompositeDicts(ConfigDicts(dicts),
                              WikiDicts())

Storage
=======
MoinMoin supports storage backends as different ways of storing wiki items.

Setup of storage is rather complex and layered, involving:

* Routing middleware that dispatches by namespace to the respective backend
* ACL checking middleware that makes sure nobody accesses something he/she is not
  authorized to access
* Indexing mixin that indexes some data automatically on commit, so items can
  be selected / retrieved faster.
* storage backends that store wiki items

create_simple_mapping
---------------------
This is a helper function to make storage setup easier when your wiki will be
using only the predefined namespaces and one kind of backend (OS file system, sqla or sqlite).
It creates a simple setup that defines storage backends for these namespaces:

* default - items that define wiki content
* users - personnal user content
* userprofiles - user metadata such as timezone, subscriptions, etc.
* help-en - English language help pages for editors
* help-common - media items used by help-en

For each namespace, the following structures are created:

* configure ACLs protecting the namespaces
* setup router middleware that dispatches to the namespace backends
* setup a indexing mixin that maintains an index of all namespaces

Call it as follows::

    from moin.storage import create_simple_mapping

    namespace_mapping, backend_mapping, acl_mapping = create_simple_mapping(
        uri=...,
        default_acl=dict(before=...,
                         default=...,
                         after=...,
                         hierarchic=..., ),
        users_acl=dict(before=...,
                       default=...,
                       after=...,
                       hierarchiv=False, ),
        userprofiles_acl=dict(before=...,
                              default=...,
                              after=...,
                              hierarchiv=False, ),
    )

The `*_acl` variables are dictionaries specifying the ACLs for
each namespace. See the docs about ACLs.

The `uri` depends on the kind of storage backend and stores you want to use,
see below. Usually it is a URL-like string in the form of::

    stores:fs:/srv/mywiki/%(backend)s/%(kind)s

`stores` is the name of the backend, followed by a colon, followed by a store
specification. `fs` is the type of the store, followed by a specification
that makes sense for the fs (filesystem) store, i.e. a path with placeholders.

`%(backend)s` placeholder will be replaced by the namespace for
the respective backend. `%(kind)s` will be replaced by 'meta' or 'data'
later.

The mapping created will look like this:

+----------------+-----------------------------+
| Namespace      | Filesystem path for storage |
+----------------+-----------------------------+
| default        | /srv/mywiki/default/        |
+----------------+-----------------------------+
| users          | /srv/mywiki/users/          |
+----------------+-----------------------------+
| userprofiles   | /srv/mywiki/userprofiles/   |
+----------------+-----------------------------+
| help-en        | /srv/mywiki/help-en/        |
+----------------+-----------------------------+
| help-common    | /srv/mywiki/help-common/    |
+----------------+-----------------------------+

If your wiki will be using custom namespaces then you cannot use the
`create_simple_mapping` method. See the `create_mapping` method in the
namespaces_ section below.

protecting middleware
---------------------
Features:

* protects access to lower storage layers by ACLs (Access Control Lists)
* makes sure there won't be ACL security issues, even if upper layers have bugs
* if you use create_simple_mapping, you just give the ACL parameters; the
  middleware will be set up automatically by moin.

routing middleware
------------------
Features:

* dispatches storage access to different backends depending on the namespace
* if you use create_simple_mapping, the router middleware will be set up
  automatically by moin.

indexing middleware
-------------------
Features:

* maintains an index for important metadata values
* speeds up looking up / selecting items
* makes it possible for lower storage layers to be simpler
* the indexing middleware will be set up automatically by moin.

stores backend
--------------
This is a backend that ties together 2 stores to form a backend: one for meta, one for data

fs store
--------
Features:

* stores into the filesystem
* store metadata and data into separate files/directories

Configuration::

    from moin.storage import create_simple_mapping

    data_dir = '/srv/mywiki/data'
    namespace_mapping, acl_mapping = create_simple_mapping(
        uri='stores:fs:{0}/%(nsname)s/%(kind)s'.format(data_dir),
        default_acl=dict(before='WikiAdmin:read,write,create,destroy',
                         default='All:read,write,create',
                         after='', ),
        users_acl=dict(before='WikiAdmin:read,write,create,destroy',
                       default='All:read,write,create',
                       after='', ),
        # userprofiles is for internal use, contains only user metadata, access denied to all
        userprofiles_acl=dict(before='All:',
                              default='',
                              after='', ),
    )


sqla store
----------
Features:

* stores data into an (SQL) database / table
* can either use 1 database per store or 1 table per store and you need to
  give different table names then
* uses slqalchemy (without the ORM) for database abstraction
* supports multiple types of databases, for example:

  - sqlite (default, comes built-into Python)
  - postgresql
  - mysql
  - and others, see sqlalchemy docs.

`uri` for `create_simple_mapping` looks like e.g.::

    stores:sqla:sqlite:////srv/mywiki/data/mywiki_%(nsname)s_%(kind).db
    stores:sqla:sqlite:////srv/mywiki/data/mywiki_%(nsname)s.db::%(kind)s
    stores:sqla:mysql://myuser:mypassword@localhost/mywiki_%(nsname)s::%(kind)s
    stores:sqla:postgres://myuser:mypassword@localhost/mywiki_%(nsname)s::%(kind)s

The uri part after "sqla:" is like::

    DBURI::TABLENAME

Please see the sqlalchemy docs about the DBURI part.

Grant 'myuser' (his password: 'mypassword') full access to these databases.


sqlite store
------------
Features:

* directly talks to sqlite, without using sqlalchemy
* stores data into an sqlite database, which is a single file
* can either use 1 database per store or 1 table per store and you need to
  give different table names then
* can optionally compress/decompress the data using zlib: default compression
  level is 0, which means "do not compress"

`uri` for `create_simple_mapping` looks like e.g.::

    stores:sqlite:/srv/mywiki/data/mywiki_%(nsname)s_%(kind)s.db
    stores:sqlite:/srv/mywiki/data/mywiki_%(nsname)s.db::%(kind)s
    stores:sqlite:/srv/mywiki/data/mywiki_%(nsname)s.db::%(kind)s::1

The uri part after "sqlite:" is like::

    PATH::TABLENAME::COMPRESSION

It uses "::" as separator to support windows pathes which may have ":" after
the drive letter.


memory store
--------------
Features:

* keeps everything in RAM
* if your system or the moin process crashes, all data is lost, so definitely not for production use
* mostly intended for testing
* single process only

.. todo:

   add memory store configuration example


fileserver backend
------------------
Features:

* exposes a part of the filesystem as read-only wiki items

  + files will show up as wiki items

    - with 1 revision
    - with as much metadata as can be made up from the filesystem metadata
  + directories will show up as index items, listing links to their contents
* might be useful together with SMBMount pseudo-authenticator

.. _namespaces:

namespaces
----------
Moin has support for multiple namespaces. You can configure them per your needs.
URLs for items within a namespace are similar to sub-items.

To configure custom namespaces, find the section in wikiconfig.py that looks similar to this::

    namespaces = {
        # maps namespace name -> backend name
        # these 3 standard namespaces are required, these have separate backends
        NAMESPACE_DEFAULT: 'default',
        NAMESPACE_USERS: 'users',
        NAMESPACE_USERPROFILES: 'userprofiles',
        # namespaces for editor help files are optional, if unwanted delete here and in backends and acls
        NAMESPACE_HELP_COMMON: 'help-common',  # contains media files used by other language helps
        NAMESPACE_HELP_EN: 'help-en',  # replace this with help-de, help-ru, help-pt_BR etc.
        # define custom namespaces using the default backend
        # 'foo': 'default',
        # custom namespace with a separate backend (a wiki/data/bar directory will be created)
        # 'bar': 'bar',
    }
    backends = {
        # maps backend name -> storage
        # the feature to use different storage types for each namespace is not implemented so use None below.
        # the storage type for all backends is set in 'uri' above,
        # all values in `namespace` dict must be defined as keys in `backends` dict
        'default': None,
        'users': None,
        'userprofiles': None,
        # help namespaces are optional
        'help-common': None,
        'help-en': None,
        # required for bar namespace if defined above
        # 'bar': None,
    }
    acls = {
        # maps namespace name -> acl configuration dict for that namespace
        #
        # One way to customize this for large wikis is to create a TrustedEditorsGroup item with
        # ACL = "TrustedEditorsGroup:read,write All:"
        # add a list of user names under the item's User Group metadata heading. Item content does not matter.
        # Every user in YOUR-TRUSTED-EDITOR-GROUP will be able to add/delete users.
        #
        # most wiki data will be stored in NAMESPACE_DEFAULT
        NAMESPACE_DEFAULT: dict(
            before='YOUR-SUPER-EDITOR:read,write,create,destroy,admin',
            default='YOUR-TRUSTED-EDITORS-GROUP:read,write,create All:read',
            after='',
            hierarchic=False, ),
        # user home pages should be stored here
        NAMESPACE_USERS: dict(
            before='YOUR-SUPER-EDITOR:read,write,create,destroy,admin',
            default='YOUR-TRUSTED-EDITORS-GROUP:read,write,create All:read',
            after='',
            # True enables possibility of an admin creating ACL rules for a user's subpages
            hierarchic=True, ),
        # contains user data that must be kept secret, dis-allow access for all
        NAMESPACE_USERPROFILES: dict(
            before='All:',
            default='',
            after='',
            hierarchic=False, ),
        # editor help namespacess are optional
        'help-common': dict(
            before='YOUR-SUPER-EDITOR:read,write,create,destroy,admin',
            default='YOUR-TRUSTED-EDITORS-GROUP:read,write,create All:read',
            after='',
            hierarchic=False, ),
        'help-en': dict(
            before='YOUR-SUPER-EDITOR:read,write,create,destroy,admin',
            default='YOUR-TRUSTED-EDITORS-GROUP:read,write,create All:read',
            after='',
            hierarchic=False, ),
    }
    namespace_mapping, backend_mapping, acl_mapping = create_mapping(uri, namespaces, backends, acls, )
    # define mapping of namespaces to unique item_roots (home pages within namespaces).
    root_mapping = {'users': 'UserHome', }
    # default root, use this value by default for all namespaces
    default_root = 'Home'

Edit the above renaming or deleting the lines with foo and bar and adding the desired custom namespaces.
Be sure all the names in the `namespaces` dict are also added to the `acls` dict.  All of the values in the
namespaces dict must be included as keys in the backends dict.

There cannot be an item with the same name as a namespace. Using the example above, if import19 is used
to convert a moin 1.9 wiki to moin 2.0, then an item `foo` would be renamed to `foo/fooHome`.

.. _mail-configuration:

Mail configuration
==================

Sending E-Mail
--------------
Moin can optionally send E-Mail. Possible uses:

* send out item change notifications
* enable users to reset forgotten passwords
* inform admins about runtime exceptions

You need to configure some settings before sending E-Mail can be supported::

    # the "from:" address [Unicode]
    mail_from = "wiki <wiki@example.org>"

    # a) using an SMTP server, e.g. "mail.provider.com" with optional `:port`
    appendix, which defaults to 25 (set None to disable mail)
    mail_smarthost = "smtp.example.org"

    # if you need to use SMTP AUTH at your mail_smarthost:
    #mail_username = "smtp_username"
    #mail_password = "smtp_password"

    # b) alternatively to using SMTP, you can use the sendmail commandline tool:
    #mail_sendmail = "/usr/sbin/sendmail -t -i"


.. todo::

   describe more moin configuration

Admin Traceback E-Mails
-----------------------
If you want to enable admins to receive Python tracebacks, you need to configure
the following::

    # list of admin emails
    admin_emails = ["admin <admin@example.org>"]

    # send tracebacks to admins
    email_tracebacks = True


Please also check the logging configuration example in `contrib/logging/email`.

User E-Mail Address Verification
--------------------------------

At account creation time, Moin can require new users to verify their E-Mail
address by clicking a link that is sent to them.

Make sure that Moin is able to send E-Mails (see previous section) and add the
following line to your configuration file to enable this feature::

    user_email_verification = True


=======================
Framework Configuration
=======================

Things you may want to configure for Flask and its extensions (see
their docs for details)::

 # for Flask
 SECRET_KEY = 'you need to change this so it is really secret'
 DEBUG = False  # use True for development only, not for public sites!
 TESTING = False  # if true, some servers will detect file changes and restart
 #SESSION_COOKIE_NAME = 'session'
 #PERMANENT_SESSION_LIFETIME = timedelta(days=31)
 #USE_X_SENDFILE = False
 #LOGGER_NAME = 'MoinMoin'

 # for Flask-Caching:
 #CACHE_TYPE = 'filesystem'
 #CACHE_DIR = '/path/to/flask-cache-dir'
 #CACHE_THRESHOLD = 300  # expiration time in seconds


=====================
Logging Configuration
=====================

By default, logging is configured to emit output on `stderr`. This will work
well for the built-in server (it will show up on the console) or for Apache2 and similar
(logging will be put into error.log).

Logging is very configurable and flexible due to the use of the `logging`
module of the Python standard library.

The configuration file format is described there:

https://docs.python.org/3/library/logging.config.html#configuration-file-format


There are also some logging configurations in the
`contrib/logging/` directory.

Logging configuration needs to be done very early, usually it will be done
from your adaptor script, e.g. moin.wsgi::

    from moin import log
    log.load_config('contrib/logging/logfile')

You have to fix that path to use a logging configuration matching your
needs (use an absolute path).

Please note that the logging configuration has to be a separate file, so don't
try this in your wiki configuration file!
