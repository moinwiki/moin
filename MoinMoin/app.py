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

# do this early, but not in MoinMoin/__init__.py because we need to be able to
# "import MoinMoin" from setup.py even before flask, werkzeug, ... is installed.
from MoinMoin.util import monkeypatch

from flask import Flask, request, session
from flask import current_app as app
from flask import g as flaskg

from flaskext.cache import Cache
from flaskext.themes import setup_themes

from werkzeug.exceptions import HTTPException

from jinja2 import ChoiceLoader, FileSystemLoader

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.i18n import i18n_init
from MoinMoin.i18n import _, L_, N_

from MoinMoin.themes import setup_jinja_env, themed_error

def create_app(config=None):
    """simple wrapper around create_app_ext() for flask-script"""
    return create_app_ext(flask_config_file=config)


def create_app_ext(flask_config_file=None, flask_config_dict=None,
                   moin_config_class=None, warn_default=True, **kwargs
                  ):
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
    app = Flask('MoinMoin')
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
        from MoinMoin.config.default import DefaultConfig as Config
    for key, value in kwargs.iteritems():
        setattr(Config, key, value)
    if Config.secrets is None:
        # reuse the secret configured for flask (which is required for sessions)
        Config.secrets = app.config.get('SECRET_KEY')
    app.cfg = Config()
    clock.stop('create_app load config')
    clock.start('create_app register')
    # register converters
    from werkzeug.routing import PathConverter
    app.url_map.converters['itemname'] = PathConverter
    # register modules, before/after request functions
    from MoinMoin.apps.frontend import frontend
    frontend.before_request(before_wiki)
    frontend.after_request(after_wiki)
    app.register_module(frontend)
    from MoinMoin.apps.admin import admin
    admin.before_request(before_wiki)
    admin.after_request(after_wiki)
    app.register_module(admin, url_prefix='/+admin')
    from MoinMoin.apps.feed import feed
    feed.before_request(before_wiki)
    feed.after_request(after_wiki)
    app.register_module(feed, url_prefix='/+feed')
    from MoinMoin.apps.misc import misc
    misc.before_request(before_wiki)
    misc.after_request(after_wiki)
    app.register_module(misc, url_prefix='/+misc')
    from MoinMoin.apps.serve import serve
    app.register_module(serve, url_prefix='/+serve')
    clock.stop('create_app register')
    clock.start('create_app flask-cache')
    cache = Cache()
    cache.init_app(app)
    app.cache = cache
    clock.stop('create_app flask-cache')
    # init storage
    clock.start('create_app init backends')
    app.unprotected_storage, app.storage = init_backends(app)
    clock.stop('create_app init backends')
    clock.start('create_app index rebuild')
    if app.cfg.index_rebuild:
        app.unprotected_storage.index_rebuild() # XXX run this from a script
    clock.stop('create_app index rebuild')
    clock.start('create_app load/save xml')
    import_export_xml(app)
    clock.stop('create_app load/save xml')
    clock.start('create_app flask-babel')
    i18n_init(app)
    clock.stop('create_app flask-babel')
    # configure templates
    clock.start('create_app flask-themes')
    setup_themes(app)
    if app.cfg.template_dirs:
        app.jinja_env.loader = ChoiceLoader([
            FileSystemLoader(app.cfg.template_dirs),
            app.jinja_env.loader,
        ])
    app.error_handlers[403] = themed_error
    clock.stop('create_app flask-themes')
    clock.stop('create_app total')
    del clock
    return app

def destroy_app(app):
    deinit_backends(app)


from MoinMoin.util.clock import Clock
from MoinMoin.storage.error import StorageError
from MoinMoin.storage.serialization import serialize, unserialize
from MoinMoin.storage.backends import router, acl, memory
from MoinMoin import auth, config, user


def init_backends(app):
    """ initialize the backend """
    # A ns_mapping consists of several lines, where each line is made up like this:
    # mountpoint, unprotected backend, protection to apply as a dict
    ns_mapping = app.cfg.namespace_mapping
    index_uri = app.cfg.router_index_uri
    # Just initialize with unprotected backends.
    unprotected_mapping = [(ns, backend) for ns, backend, acls in ns_mapping]
    unprotected_storage = router.RouterBackend(unprotected_mapping, index_uri=index_uri)
    # Protect each backend with the acls provided for it in the mapping at position 2
    amw = acl.AclWrapperBackend
    protected_mapping = [(ns, amw(app.cfg, backend, **acls)) for ns, backend, acls in ns_mapping]
    storage = router.RouterBackend(protected_mapping, index_uri=index_uri)
    return unprotected_storage, storage

def deinit_backends(app):
    app.storage.close()
    app.unprotected_storage.close()


def import_export_xml(app):
    # If the content was already pumped into the backend, we don't want
    # to do that again. (Works only until the server is restarted.)
    xmlfile = app.cfg.load_xml
    if xmlfile:
        app.cfg.load_xml = None
        tmp_backend = router.RouterBackend([('/', memory.MemoryBackend())],
                                           index_uri='sqlite://')
        unserialize(tmp_backend, xmlfile)
        # TODO optimize this, maybe unserialize could count items it processed
        item_count = 0
        for item in tmp_backend.iteritems():
            item_count += 1
        logging.debug("loaded xml into tmp_backend: %s, %d items" % (xmlfile, item_count))
        try:
            # In case the server was restarted we cannot know whether
            # the xml data already exists in the target backend.
            # Hence we check the existence of the items before we unserialize
            # them to the backend.
            backend = app.unprotected_storage
            for item in tmp_backend.iteritems():
                item = backend.get_item(item.name)
        except StorageError:
            # if there is some exception, we assume that backend needs to be filled
            # we need to use it as unserialization target so that update mode of
            # unserialization creates the correct item revisions
            logging.debug("unserialize xml file %s into %r" % (xmlfile, backend))
            unserialize(backend, xmlfile)
    else:
        item_count = 0

    # XXX wrong place / name - this is a generic preload functionality, not just for tests
    # To make some tests happy
    app.cfg.test_num_pages = item_count

    xmlfile = app.cfg.save_xml
    if xmlfile:
        app.cfg.save_xml = None
        backend = app.unprotected_storage
        serialize(backend, xmlfile)


def setup_user():
    """ Try to retrieve a valid user object from the request, be it
    either through the session or through a login. """
    # init some stuff for auth processing:
    flaskg._login_multistage = None
    flaskg._login_multistage_name = None
    flaskg._login_messages = []

    # first try setting up from session
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
        userobj = user.User(auth_method='invalid')
    # if we have a valid user we store it in the session
    if userobj.valid:
        session['user.id'] = userobj.id
        session['user.auth_method'] = userobj.auth_method
        session['user.auth_attribs'] = userobj.auth_attribs
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
        flaskg.unprotected_storage = app.unprotected_storage

        try:
            flaskg.user = setup_user()
        except HTTPException as e:
            # this makes stuff like abort(redirect(...)) work
            return app.handle_http_exception(e)

        flaskg.dicts = app.cfg.dicts()
        flaskg.groups = app.cfg.groups()

        flaskg.content_lang = app.cfg.language_default
        flaskg.current_lang = app.cfg.language_default

        flaskg.storage = app.storage

        setup_jinja_env()
    finally:
        flaskg.clock.stop('init')

    # if return value is not None, it is the final response


def after_wiki(response):
    """
    Stop timers.
    """
    logging.debug("running after_wiki")
    try:
        flaskg.clock.stop('total')
        del flaskg.clock
    except AttributeError:
        # can happen if after_wiki() is called twice, e.g. by unit tests.
        pass
    return response

