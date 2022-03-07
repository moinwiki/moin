# -*- coding: utf-8 -*-
"""
MoinMoin Wiki Configuration - see https://moin-20.readthedocs.org/en/latest/admin/configure.html

This file should be customized before creating content and adding user registrations.

This starting configuration is designed to run moin using the built-in server to serve files
to browsers running on the local PC.

The security settings below are very relaxed, and not suitable for wikis
serving files to the general public on the web.
"""

import os
from moin.config.default import DefaultConfig, _default_password_checker
from moin.storage import create_simple_mapping
from moin.utils.interwiki import InterWikiMap


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
        moin index-create -s -i                                 # creates empty wiki, OR
        moin import19 -s -i --data_dir <path to 1.9 wiki/data>  # import 1.9 data, OR
        moin index-create; moin load-sample; moin index-build   # creates wiki with sample data
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

    # setup static files' serving:
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

    # default theme is topside
    # theme_default = "modernized"  # or basic or topside_cms

    # read about PRIVACY ISSUES in docs before uncommenting the line below to use gravatars
    # user_use_gravatar = True

    # read about SECURITY ISSUES in docs before uncommenting the line below allowing users
    # to edit style attributes in HTML and Markdown items
    # allow_style_attributes = True

    # default passwords are required to be => 8 characters with minimum of 5 unique characters
    # password_checker = None  # no password length or quality checking
    # password_checker = lambda cfg, name, pw: _default_password_checker(cfg, name, pw, min_length=8, min_different=5)  # default

    # optional, configure email, uncomment line below and choose (a) or (b)
    # mail_from = "wiki <wiki@example.org>"  # the "from:" address [Unicode]
    # (a) using an SMTP server, e.g. "mail.provider.com" with optional `:port`appendix, which defaults to 25 (set None to disable mail)
    # mail_smarthost = "smtp.example.org"
    # mail_username = "smtp_username"  # if you need to use SMTP AUTH at your mail_smarthost:
    # mail_password = "smtp_password"
    # (b) an alternative to SMTP is the sendmail commandline tool:
    # mail_sendmail = "/usr/sbin/sendmail -t -i"

    # list of admin emails
    admin_emails = []
    # send tracebacks to admins
    email_tracebacks = False

    # options for new user registration
    # registration_only_by_superuser = True  # disables self-registration, recommended for public wikis on internet
    # registration_hint = 'To request an account, see bottom of <a href="/Home">Home</a> page.'

    # add or remove packages - see https://bitbucket.org/thomaswaldmann/xstatic for info about xstatic
    # it is uncommon to change these because of local customizations
    from xstatic.main import XStatic
    # names below must be package names
    mod_names = [
        'jquery', 'jquery_file_upload',
        'bootstrap',
        'font_awesome',
        'ckeditor',
        'autosize',
        'svgedit_moin', 'twikidraw_moin', 'anywikidraw',
        'jquery_tablesorter',
        'pygments',
    ]
    pkg = __import__('xstatic.pkg', fromlist=mod_names)
    for mod_name in mod_names:
        mod = getattr(pkg, mod_name)
        xs = XStatic(mod, root_url='/static', provider='local', protocol='http')
        serve_files[xs.name] = xs.base_dir

    # create a super user who will have access to administrative functions
    # acl_functions = '+YourName:superuser'
    # OR, create several WikiGroups and create several superusers
    # SuperGroup and TrustedEditorGroup reference WikiGroups you must create
    # acl_functions = '+YourName:superuser SuperGroup:superuser'

    # This provides a simple default setup for your backend configuration.
    # 'stores:fs:...' indicates that you want to use the filesystem backend.
    # Alternatively you can set up the mapping yourself (see HelpOnStorageConfiguration).
    namespace_mapping, backend_mapping, acl_mapping = create_simple_mapping(
        uri='stores:fs:{0}/%(backend)s/%(kind)s'.format(data_dir),
        # XXX we use rather relaxed ACLs for the development wiki:
        default_acl=dict(before='',
                         default='All:read,write,create,destroy,admin',
                         after='',
                         hierarchic=False, ),
        users_acl=dict(before='',
                       default='All:read,write,create,destroy,admin',
                       after='',
                       hierarchic=False, ),
        # userprofiles contain only metadata, no content will be created
        userprofiles_acl=dict(before='All:',
                              default='',
                              after='',
                              hierarchic=False, ),
    )

    """
    secrets = {
        'security/ticket': 'EnterDifferentSecretStringHere',
    }
    """


# flask settings require all caps
MOINCFG = Config  # adding MOINCFG=<path> to OS environment overrides CWD
# Flask settings - see the flask documentation about their meaning
SECRET_KEY = 'you need to change this so it is really secret'
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
