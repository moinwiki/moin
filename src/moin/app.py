# Copyright: 2000-2006 by Juergen Hermann <jh@web.de>
# Copyright: 2002-2011 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:FlorianKrupicka
# Copyright: 2010 MoinMoin:DiogenesAugusto
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - wsgi application setup and related code

Use create_app(config) to create the WSGI application (using Flask).
"""

from __future__ import absolute_import, division

import os
import sys

# do this early, but not in moin/__init__.py because we need to be able to
# "import moin" from setup.py even before flask, werkzeug, ... is installed.
from moin.utils import monkeypatch

from flask import Flask, request, session
from flask import current_app as app
from flask import g as flaskg

from flask_caching import Cache
from flask_theme import setup_themes

from jinja2 import ChoiceLoader, FileSystemLoader

from moin.constants.misc import ANON
from moin.i18n import i18n_init
from moin.i18n import _, L_, N_
from moin.themes import setup_jinja_env, themed_error
from moin.utils.clock import Clock
from moin.storage.middleware import protecting, indexing, routing
from moin import auth, user

from moin import log
logging = log.getLogger(__name__)


if os.getcwd() not in sys.path and '' not in sys.path:
    # required in cases where wikiconfig_local.py imports wikiconfig_editme.py, see #698
    sys.path.append(os.getcwd())


def create_app(config=None, create_index=False, create_storage=False):
    """
    simple wrapper around create_app_ext() for flask-script
    """
    return create_app_ext(flask_config_file=config,
                          create_index=create_index,
                          create_storage=create_storage)


def create_app_ext(flask_config_file=None, flask_config_dict=None,
                   moin_config_class=None, warn_default=True, **kwargs):
    """
    Factory for moin wsgi apps

    :param flask_config_file: a flask config file name (may have a MOINCFG class),
                              if not given, a config pointed to by MOINCFG env var
                              will be loaded (if possible).
    :param flask_config_dict: a dict used to update flask config (applied after
                              flask_config_file was loaded [if given])
    :param moin_config_class: if you give this, it'll be instantiated as app.cfg,
                              otherwise it'll use MOINCFG from flask config. If that
                              also is not there, it'll use the DefaultConfig built
                              into MoinMoin.
    :param warn_default: emit a warning if moin falls back to its builtin default
                         config (maybe user forgot to specify MOINCFG?)
    :param kwargs: if you give additional keyword args, the keys/values will get patched
                   into the moin configuration class (before its instance is created)
    """
    clock = Clock()
    clock.start('create_app total')
    app = Flask('moin')

    clock.start('create_app load config')
    if flask_config_file:
        app.config.from_pyfile(flask_config_file)
    else:
        if not app.config.from_envvar('MOINCFG', silent=True):
            # no MOINCFG env variable set, try stuff in cwd:
            from os import path
            flask_config_file = path.abspath('wikiconfig_local.py')
            if not path.exists(flask_config_file):
                flask_config_file = path.abspath('wikiconfig.py')
                if not path.exists(flask_config_file):
                    flask_config_file = None
            if flask_config_file:
                app.config.from_pyfile(flask_config_file)
    if flask_config_dict:
        app.config.update(flask_config_dict)
    Config = moin_config_class
    if not Config:
        Config = app.config.get('MOINCFG')
    if not Config:
        if warn_default:
            logging.warning("using builtin default configuration")
        from moin.config.default import DefaultConfig as Config
    for key, value in kwargs.items():
        setattr(Config, key, value)
    if Config.secrets is None:
        # reuse the secret configured for flask (which is required for sessions)
        Config.secrets = app.config.get('SECRET_KEY')
    app.cfg = Config()
    clock.stop('create_app load config')
    clock.start('create_app register')
    # register converters
    from werkzeug.routing import BaseConverter

    class ItemNameConverter(BaseConverter):
        """Like the default :class:`UnicodeConverter`, but it also matches
        slashes (except at the beginning AND end).
        This is useful for wikis and similar applications::

            Rule('/<itemname:wikipage>')
            Rule('/<itemname:wikipage>/edit')
        """
        regex = '[^/]+?(/[^/]+?)*'
        weight = 200

    app.url_map.converters['itemname'] = ItemNameConverter
    # register modules, before/after request functions
    from moin.apps.frontend import frontend
    frontend.before_request(before_wiki)
    frontend.teardown_request(teardown_wiki)
    app.register_blueprint(frontend)
    from moin.apps.admin import admin
    admin.before_request(before_wiki)
    admin.teardown_request(teardown_wiki)
    app.register_blueprint(admin, url_prefix='/+admin')
    from moin.apps.feed import feed
    feed.before_request(before_wiki)
    feed.teardown_request(teardown_wiki)
    app.register_blueprint(feed, url_prefix='/+feed')
    from moin.apps.misc import misc
    misc.before_request(before_wiki)
    misc.teardown_request(teardown_wiki)
    app.register_blueprint(misc, url_prefix='/+misc')
    from moin.apps.serve import serve
    app.register_blueprint(serve, url_prefix='/+serve')
    clock.stop('create_app register')
    clock.start('create_app flask-cache')
    # the 'simple' caching uses a dict and is not thread safe according to the docs.
    cache = Cache(config={'CACHE_TYPE': 'simple'})
    cache.init_app(app)
    app.cache = cache
    clock.stop('create_app flask-cache')
    # init storage
    clock.start('create_app init backends')
    init_backends(app)
    clock.stop('create_app init backends')
    clock.start('create_app flask-babel')
    i18n_init(app)
    clock.stop('create_app flask-babel')
    # configure templates
    clock.start('create_app flask-theme')
    setup_themes(app)
    if app.cfg.template_dirs:
        app.jinja_env.loader = ChoiceLoader([
            FileSystemLoader(app.cfg.template_dirs),
            app.jinja_env.loader,
        ])
    app.register_error_handler(403, themed_error)
    clock.stop('create_app flask-theme')
    clock.stop('create_app total')
    del clock
    return app


def destroy_app(app):
    deinit_backends(app)


def init_backends(app):
    """
    initialize the backends
    """
    # A ns_mapping consists of several lines, where each line is made up like this:
    # mountpoint, unprotected backend
    # Just initialize with unprotected backends.
    app.router = routing.Backend(app.cfg.namespace_mapping, app.cfg.backend_mapping)
    if app.cfg.create_storage:
        app.router.create()
    app.router.open()
    app.storage = indexing.IndexingMiddleware(app.cfg.index_storage, app.router,
                                              wiki_name=app.cfg.interwikiname,
                                              acl_rights_contents=app.cfg.acl_rights_contents)
    if app.cfg.create_index:
        app.storage.create()
    app.storage.open()


def deinit_backends(app):
    app.storage.close()
    app.router.close()
    if app.cfg.destroy_index:
        app.storage.destroy()
    if app.cfg.destroy_storage:
        app.router.destroy()


def setup_user():
    """
    Try to retrieve a valid user object from the request, be it
    either through the session or through a login.
    """
    # init some stuff for auth processing:
    flaskg._login_multistage = None
    flaskg._login_multistage_name = None
    flaskg._login_messages = []

    # first try setting up from session
    try:
        userobj = auth.setup_from_session()
    except KeyError:
        # error caused due to invalid cookie, recreating session
        session.clear()
        userobj = auth.setup_from_session()

    # then handle login/logout forms
    form = request.values.to_dict()
    if 'login_submit' in form:
        # this is a real form, submitted by POST
        userobj = auth.handle_login(userobj, **form)
    elif 'logout_submit' in form:
        # currently just a GET link
        userobj = auth.handle_logout(userobj)
    else:
        userobj = auth.handle_request(userobj)

    # if we still have no user obj, create a dummy:
    if not userobj:
        userobj = user.User(name=ANON, auth_method='invalid')
    # if we have a valid user we store it in the session
    if userobj.valid:
        session['user.itemid'] = userobj.itemid
        session['user.trusted'] = userobj.trusted
        session['user.auth_method'] = userobj.auth_method
        session['user.auth_attribs'] = userobj.auth_attribs
        session['user.session_token'] = userobj.get_session_token()
    return userobj


def before_wiki():
    """
    Setup environment for wiki requests, start timers.
    """
    logging.debug("running before_wiki")
    flaskg.clock = Clock()
    flaskg.clock.start('total')
    flaskg.clock.start('init')
    try:
        flaskg.unprotected_storage = app.storage

        flaskg.user = setup_user()
        flaskg.storage = protecting.ProtectingMiddleware(app.storage, flaskg.user, app.cfg.acl_mapping)

        flaskg.dicts = app.cfg.dicts()
        flaskg.groups = app.cfg.groups()

        flaskg.content_lang = app.cfg.language_default
        flaskg.current_lang = app.cfg.language_default

        setup_jinja_env()

        # request.user_agent == '' if this is pytest
        flaskg.add_lineno_attr = request.user_agent and flaskg.user.edit_on_doubleclick
    finally:
        flaskg.clock.stop('init')

    # if return value is not None, it is the final response


def teardown_wiki(response):
    """
    Teardown environment of wiki requests, stop timers.
    """
    logging.debug("running teardown_wiki")
    try:
        flaskg.clock.stop('total')
        del flaskg.clock
    except AttributeError:
        # can happen if teardown_wiki() is called twice, e.g. by unit tests.
        pass
    if hasattr(flaskg, 'edit_utils'):
        try:
            flaskg.edit_utils.db.close()
        except AttributeError:
            pass
    return response
