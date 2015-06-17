# -*- coding: utf-8 -*-
"""
MoinMoin Wiki Configuration - see https://moin-20.readthedocs.org/en/latest/admin/configure.html

This configuration is designed to run moin from a workdir using
the built-in server. Wiki admins who install moin via a mercurial repository rather
than a release package may opt to follow the developer instructions below to
reduce merge issues when pulling updates.


DEVELOPERS! Do not add your configuration items here - you could accidentally
commit them! Instead, follow these steps:

(1) In this directory, create a wikiconfig_local.py file containing the following one line of code:

from wikiconfig_editme import *  # enable auto reload when wikiconfig_editme.py changes

(2) Create a second file named wikiconfig_editme.py with the following six lines of code:

from wikiconfig import *
class LocalConfig(Config):
    configuration_item_1 = 'value1'  # overlay this with local customizations
MOINCFG = LocalConfig
SECRET_KEY = 'you need to change this so it is really secret'
DEBUG = True

(3) Overlay the 3rd line in wikiconfig_editme.py by copying any or all of the indented
    lines from "class Config" below.

(4) Customize wikiconfig_editme.py as needed. Not all customization options are included
    here, read the docs for other options.
"""

import os

from MoinMoin.config.default import DefaultConfig, _default_password_checker
from MoinMoin.storage import create_simple_mapping
from MoinMoin.util.interwiki import InterWikiMap


class Config(DefaultConfig):

    # We assume this structure for a mercurial clone or simple "unpack and run" scenario:
    # moin-2.0/                     # wikiconfig_dir points here: clone root or unpack directory, contains this file.
    #     wikiconfig.py             # the file you are reading now.
    #     wiki/                     # instance_dir variable points here: created by running "./m sample" or "./m new-wiki" commands.
    #         data/                 # data_dir variable points here.
    #         index/                # index_storage variable points here.
    #     contrib/
    #         interwiki/
    #             intermap.txt      # interwiki_map variable points here.
    #     docs/
    #         _build/
    #             html/             # serve_files['docs']: html docs made by sphinx, create by running "./m docs" command.
    #     wiki_local/               # serve_files['wiki_local']: store custom logos, CSS, templates, etc. here
    # If that's not true, adjust these paths
    wikiconfig_dir = os.path.abspath(os.path.dirname(__file__))
    instance_dir = os.path.join(wikiconfig_dir, 'wiki')
    data_dir = os.path.join(instance_dir, 'data')
    index_storage = 'FileStorage', (os.path.join(instance_dir, "index"), ), {}
    # setup static files' serving:
    serve_files = dict(
        docs=os.path.join(wikiconfig_dir, 'docs', '_build', 'html'),  # html docs made by sphinx
        wiki_local=os.path.join(wikiconfig_dir, 'wiki_local'),  # store custom logos, CSS, templates, etc. here
    )
    # copy templates/snippets.html to directory below and edit per requirements to customize logos, etc.
    template_dirs = [os.path.join(wikiconfig_dir, 'wiki_local'), ]

    # it is required that you set this to a unique, stable and non-empty name:
    interwikiname = u'MyMoinMoin'
    # load the interwiki map from intermap.txt:
    interwiki_map = InterWikiMap.from_file(os.path.join(wikiconfig_dir, 'contrib', 'interwiki', 'intermap.txt')).iwmap
    # we must add entries for 'Self' and our interwikiname, change these if you are not running the built-in desktop server:
    interwiki_map[interwikiname] = 'http://127.0.0.1:8080/'
    interwiki_map['Self'] = 'http://127.0.0.1:8080/'

    # sitename is displayed in heading of all wiki pages
    sitename = u'My MoinMoin'

    # default theme is basic
    # theme_default = u"modernized"

    # read about PRIVACY ISSUES in docs before uncommenting the line below to use gravatars
    # user_use_gravatar = True

    # read about SECURITY ISSUES in docs before uncommenting the line below allowing users
    # to edit style attributes in HTML and Markdown items
    # allow_style_attributes = True

    # default passwords are required to be => 8 characters with minimum of 5 unique characters
    # password_checker = None  # no password length or quality checking
    # password_checker = lambda cfg, name, pw: _default_password_checker(cfg, name, pw, min_length=8, min_different=5)  # default

    # optional, configure email, uncomment line below and choose (a) or (b)
    # mail_from = u"wiki <wiki@example.org>"  # the "from:" address [Unicode]
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
    # acl_functions = u'+YourName:superuser'
    # OR, create several WikiGroups and create several superusers and turn off textchas for selected users
    # SuperGroup and TrustedEditorGroup reference WikiGroups you must create
    # acl_functions = u'+YourName:superuser SuperGroup:superuser YourName:notextcha TrustedEditorGroup:notextcha'

    # This provides a simple default setup for your backend configuration.
    # 'stores:fs:...' indicates that you want to use the filesystem backend.
    # Alternatively you can set up the mapping yourself (see HelpOnStorageConfiguration).
    namespace_mapping, backend_mapping, acl_mapping = create_simple_mapping(
        uri='stores:fs:{0}/%(backend)s/%(kind)s'.format(data_dir),
        # XXX we use rather relaxed ACLs for the development wiki:
        default_acl=dict(before=u'',
                         default=u'All:read,write,create,destroy,admin',
                         after=u'',
                         hierarchic=False, ),
        userprofiles_acl=dict(before=u'',
                              default=u'All:read,write,create,destroy,admin',
                              after=u'',
                              hierarchic=False, ),
    )

    # uncomment and improve block below to enable textchas
    """
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
    #
    secrets = {
        'security/textcha': 'EnterSecretStringHere',
        'security/ticket': 'EnterDifferentSceretStringHere',
    }
    """


MOINCFG = Config  # Flask requires uppercase
# Flask settings - see the flask documentation about their meaning
SECRET_KEY = 'you need to change this so it is really secret'
# DEBUG = False # use True for development only, not for public sites!
# TESTING = False
# SESSION_COOKIE_NAME = 'session'
# PERMANENT_SESSION_LIFETIME = timedelta(days=31)
# USE_X_SENDFILE = False
# LOGGER_NAME = 'MoinMoin'
# config for flask-cache:
# CACHE_TYPE = 'filesystem'
# CACHE_DIR = '/path/to/flask-cache-dir'
