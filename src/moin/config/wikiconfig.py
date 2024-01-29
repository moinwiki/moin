# -*- coding: utf-8 -*-
"""
MoinMoin Wiki Configuration - see https://moin-20.readthedocs.io/en/latest/admin/configure.html

This file should be customized before creating content and adding user registrations.
If settings are changed after adding content and users then the indexes may
require rebuilding.

This starting configuration will run moin using the built-in server to serve files
to browsers running on the local PC. The starting security settings below are secure,
provided superuser and supereditor names are created and any wikigroups are
created with protective ACLs before allowing public access with a more robust server.

If this will be a private single-user wiki with no public access, then change the line:
    registration_only_by_superuser = True
to:
    registration_only_by_superuser = False
and change several lines containing:
    ... before='YourSuperEditor:read,write,create,destroy,admin',
to:
    ... before='All:read,write,create,destroy,admin',
and change:
    edit_locking_policy = 'lock'
to:
    edit_locking_policy = None
optional change:
    sitename = 'My MoinMoin'
Done!
"""

import os
from moin.config.default import DefaultConfig
from moin.utils.interwiki import InterWikiMap
from moin.storage import create_mapping
from moin.constants.namespaces import NAMESPACE_DEFAULT, NAMESPACE_USERPROFILES, NAMESPACE_USERS


class Config(DefaultConfig):
    """
    We assume this structure for a git clone scenario used by developers:

        moin/                   # clone root and wikiconfig dir, use this as CWD for ./m or moin commands
            contrib             # developer tools
            docs/
                _build/
                    html/       # local copy of moin documentation, created by running "./m docs" command
            src/
                moin/           # directory containing moin application code
            wiki/               # the wiki instance; created by running "./m sample" or "./m new-wiki" commands
                data/           # wiki data and metadata
                index/          # wiki indexes
                preview/        # edit backups created when user clicks edit Preview button
                sql/            # sql database used for edit locking
            wikiconfig.py       # main configuration file, modify this to add or change features
            wiki_local/         # use this to store custom CSS, Javascript, templates, logos, etc.
            intermap.txt        # list of external wikis used in wikilinks: [[MeatBall:InterWiki]]
        <moin-venv-python>      # virtual env is created as a sibling to moin/ by default
            bin/                # Windows calls this directory Scripts
            include             # Windows calls this directory Include
            lib/                # Windows calls this directory Lib


    OR: To install moin from pypi into a venv, enter this sequence of commands:
        <python> -m venv <myvenv>
        cd <path-to-new-myvenv>
        source bin/activate activate  # Scripts\activate.bat
        pip install wheel
        pip install moin
        moin create-instance --path <mywiki>
        cd <mywiki>
        moin index-create                                      # creates empty wiki, OR
        moin import19 --data_dir <path to 1.9 wiki/data>       # import 1.9 data, OR
        moin index-create; moin load-sample; moin index-build  # creates wiki with sample data
        to create this structure:

        <myvenv>/               # virtualenv root, moin installed in site-packages below include/
            bin/                # Windows calls this directory Scripts
            include/            # Windows calls this directory Include
            lib/                # Windows calls this directory Lib

        <mywiki>/               # wikiconfig dir, use this as CWD for moin commands after <myvenv> activated
            wiki/               # the wiki instance; created by `moin create-instance`
                data/           # wiki data and metadata
                index/          # wiki indexes
                preview/        # backups created when user clicks edit Preview button
                sql/            # sqlite database used for edit locking
            wiki-local/         # store custom CSS, Javascript, templates, logos, etc. here
            wikiconfig.py       # main configuration file, modify this to add or change features
            intermap.txt        # list of external wikis used in wikilinks: [[MeatBall:InterWiki]]

    If that's not true, adjust these paths
    """
    wikiconfig_dir = os.path.abspath(os.path.dirname(__file__))
    instance_dir = os.path.join(wikiconfig_dir, 'wiki')
    data_dir = os.path.join(instance_dir, 'data')
    index_storage = 'FileStorage', (os.path.join(instance_dir, "index"), ), {}

    # setup moin to serve static files' or change to have your webserver serve static files
    serve_files = dict(
        wiki_local=os.path.join(wikiconfig_dir, 'wiki_local'),  # store custom logos, CSS, templates, etc. here
    )
    docs = os.path.join(wikiconfig_dir, 'docs', '_build', 'html')
    if os.path.isdir(docs):
        serve_files['docs'] = docs
    else:
        # change target if a specific release or language is available
        serve_files['external_docs'] = "https://moin-20.readthedocs.io/en/latest/"

    # copy templates/snippets.html to directory below and edit per requirements to customize logos, etc.
    template_dirs = [os.path.join(wikiconfig_dir, 'wiki_local'), ]

    # it is required that you set interwikiname to a unique, stable and non-empty name.
    # Changing interwikiname on an existing wiki requires rebuilding the index.
    #     moin index-destroy; moin index-create; moin index-rebuild
    interwikiname = 'MyMoinMoin'
    # load the interwiki map from intermap.txt
    try:
        interwiki_map = InterWikiMap.from_file(os.path.join(wikiconfig_dir, 'intermap.txt')).iwmap
    except FileNotFoundError:
        interwiki_map = {}
    # we must add entries for 'Self' and our interwikiname,
    # if you are not running the built-in desktop server change these to your wiki URL
    interwiki_map[interwikiname] = 'http://127.0.0.1:8080/'
    interwiki_map['Self'] = 'http://127.0.0.1:8080/'

    # sitename is displayed in heading of all wiki pages
    sitename = 'My MoinMoin'

    # see https://www.moinmo.in/ThemeMarket for contributed moin2 themes
    # default theme is topside
    # theme_default = "modernized"  # or basic or topside_cms

    # prevent multiple users from editing an item at same time
    edit_locking_policy = 'lock'
    edit_lock_time = 20  # minutes, resets when the Preview button is clicked

    # number of quicklinks to show in navigation bar, mouseover shows all
    # only the modernized theme supports this
    expanded_quicklinks_size = 5

    # read about PRIVACY ISSUES in docs before uncommenting the line below to use gravatars
    # user_use_gravatar = True

    # read about SECURITY ISSUES in docs before uncommenting the line below allowing users
    # to edit style attributes in HTML and Markdown items
    # allow_style_attributes = True

    # default passwords are required to be => 8 characters with minimum of 5 unique characters
    # password_checker = None  # no password length or quality checking
    # from moin.config.default import _default_password_checker
    # password_checker = lambda cfg, name, pw: \
    #     _default_password_checker(cfg, name, pw, min_length=8, min_different=5)  # default

    # configure email, uncomment line below and choose (a) or (b)
    # mail_from = "wiki <wiki@example.org>"  # the "from:" address [Unicode]
    # (a) using an SMTP server, e.g. "mail.provider.com"
    # with optional `:port`appendix, which defaults to 25 (set None to disable mail)
    # mail_smarthost = "smtp.example.org"
    # mail_username = "smtp_username"  # if you need to use SMTP AUTH at your mail_smarthost:
    # mail_password = "smtp_password"
    # (b) an alternative to SMTP is the sendmail commandline tool:
    # mail_sendmail = "/usr/sbin/sendmail -t -i"

    # list of admin emails
    admin_emails = []
    # if True send tracebacks to admins
    email_tracebacks = False

    # New user registration option; if set to True use the command line to create the first superuser:
    #  moin account-create --name MyName --email MyName@x.x --password ********
    registration_only_by_superuser = True  # True disables self-registration, recommended for public wikis
    registration_hint = 'To contribute to this wiki as an editor send an email with your preferred UserName to XXX@XXX.XXX.'

    # if registration_only_by_superuser=False then making this True verifies a working email address
    # for users who self-register
    user_email_verification = False

    # Define the super user who will have access to administrative functions like user registration,
    # password reset, disabling users, etc.
    acl_functions = 'YourSuperUserName,SomeOtherSuperUserName:superuser'
    # OR, if you have a large active wiki with many administrators and editors you may want to
    # create a ConfigGroup or a WikiGroup. Group names may be used in place of user names
    # above and in ACL rules defined below. Read about it here:
    # https://moin-20.readthedocs.io/en/latest/admin/configure.html#group-backend-configuration

    # File Storage backends are recommended for most wikis
    uri = 'stores:fs:{0}/%(backend)s/%(kind)s'.format(data_dir)  # use file system for storage
    # uri = 'stores:sqlite:{0}/mywiki_%(backend)s_%(kind)s.db'.format(data_dir)  # sqlite, 1 table per db
    # uri = 'stores:sqlite:{0}/mywiki_%(backend)s.db::%(kind)s'.format(data_dir)  # sqlite, 2 tables per db
    # sqlite via SQLAlchemy
    # uri = 'stores:sqla:sqlite:///{0}/mywiki_%(backend)s_%(kind)s.db'.format(data_dir)  #  1 table per db
    # uri = 'stores:sqla:sqlite:///{0}/mywiki_%(backend)s.db:%(kind)s'.format(data_dir)  # 2 tables per db

    namespaces = {
        # maps namespace name -> backend name
        # these 3 standard namespaces are required, these have separate backends
        NAMESPACE_DEFAULT: 'default',
        NAMESPACE_USERS: 'users',
        NAMESPACE_USERPROFILES: 'userprofiles',
        # namespaces for editor help files are optional, if unwanted delete here and in backends and acls
        'help-common': 'help-common',  # contains media files used by other language helps
        'help-en': 'help-en',  # replace this with help-de, help-ru, help-pt_BR etc.
        # define custom namespaces if desired, trailing / below causes foo to be stored in default backend
        # 'foo/': 'default',
        # custom namespace with a separate backend - note absence of trailing /
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
        # One way to customize this is to create a TrustedEditorGroup item with
        # ACL = "TrustedEditorsGroup:read,write All:",
        # add a list of user names under the User Group metadata heading. Item content does not matter.
        # Every user in TrustedEditorGroup will be able to add/delete users.
        #
        # most wiki data will be stored in NAMESPACE_DEFAULT
        NAMESPACE_DEFAULT: dict(before='YourSuperEditor:read,write,create,destroy,admin',
                                default='TrustedEditorGroup:read,write,create All:read',
                                after='',
                                hierarchic=False, ),
        # user home pages should be stored here
        NAMESPACE_USERS: dict(before='YourSuperEditor:read,write,create,destroy,admin',
                              default='TrustedEditorGroup:read,write,create All:read',
                              after='',
                              # True enables possibility of an admin creating ACL rules for a user's subpages
                              hierarchic=True, ),
        # contains user data that must be kept secret, dis-allow access for all
        NAMESPACE_USERPROFILES: dict(before='All:',
                                     default='',
                                     after='',
                                     hierarchic=False, ),
        # editor help namespacess are optional
        'help-common': dict(before='YourSuperEditor:read,write,create,destroy,admin',
                            default='TrustedEditorGroup:read,write,create All:read',
                            after='',
                            hierarchic=False, ),
        'help-en': dict(before='YourSuperEditor:read,write,create,destroy,admin',
                        default='TrustedEditorGroup:read,write,create All:read',
                        after='',
                        hierarchic=False, ),
    }
    namespace_mapping, backend_mapping, acl_mapping = create_mapping(uri, namespaces, backends, acls, )
    # define mapping of namespaces to unique item_roots (home pages within namespaces).
    root_mapping = {'user': 'UserHome'}
    # default root, use this value by default for all namespaces
    default_root = 'Home'

    # add or remove packages - see https://github.com/xstatic-py/xstatic for info about xstatic
    # it is uncommon to change these because of local customizations
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


# flask settings require all caps
MOINCFG = Config  # adding MOINCFG=<path> to OS environment overrides CWD
# Flask settings - see the flask documentation about their meaning
SECRET_KEY = 'WARNING: set this to a unique string to create secure cookies'
DEBUG = False  # use True for development only, not for public sites!
TESTING = False  # built-in server (./m run) ignores TESTING and DEBUG settings
# per https://flask.palletsprojects.com/en/1.1.x/security/#set-cookie-options
SESSION_COOKIE_SECURE = False  # flask default is False
SESSION_COOKIE_HTTPONLY = True  # flask default is True
SESSION_COOKIE_SAMESITE = 'Lax'  # flask default is None
# SESSION_COOKIE_NAME = 'session'
# PERMANENT_SESSION_LIFETIME = timedelta(days=31)
# USE_X_SENDFILE = False
# LOGGER_NAME = 'MoinMoin'
# config for flask-cache:
# CACHE_TYPE = 'filesystem'
# CACHE_DIR = '/path/to/flask-cache-dir'
