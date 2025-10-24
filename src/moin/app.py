# Copyright: 2000-2006 by Juergen Hermann <jh@web.de>
# Copyright: 2002-2011 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:FlorianKrupicka
# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2023-2025 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - WSGI application setup and related code.

Use create_app(config) to create the WSGI application (using Flask).
"""

from __future__ import annotations

import os
import sys

from os import path, PathLike
from flask import Flask, request, session
from flask import current_app as app
from flask import g as flaskg

from click import get_current_context

from flask_caching import Cache
from flask_theme import setup_themes

from jinja2 import ChoiceLoader, FileSystemLoader
from whoosh.index import EmptyIndexError

from moin import auth, user, config
from moin.constants.misc import ANON
from moin.i18n import i18n_init
from moin.search import SearchForm
from moin.storage.middleware import protecting, indexing, routing
from moin.themes import setup_jinja_env, themed_error, ThemeSupport
from moin.utils import monkeypatch  # noqa
from moin.utils.clock import Clock
from moin.utils.forms import make_generator
from moin.wikiutil import WikiLinkAnalyzer

from moin import log

from typing import Any

logging = log.getLogger(__name__)


if os.getcwd() not in sys.path and "" not in sys.path:
    # required in cases where wikiconfig_local.py imports wikiconfig_editme.py, see #698
    sys.path.append(os.getcwd())


def create_app(config: str | PathLike[str] | None = None) -> Flask:
    """
    Simple wrapper around create_app_ext().
    """
    return create_app_ext(flask_config_file=config)


def create_app_ext(
    flask_config_file: str | PathLike[str] | None = None,
    flask_config_dict: dict[str, Any] | None = None,
    moin_config_class: type | None = None,
    warn_default: bool = True,
    **kwargs,
) -> Flask:
    """
    Factory for Moin WSGI apps.

    :param flask_config_file: A Flask config file name (may define a MOINCFG class).
                              If not given, a config pointed to by the MOINCFG env var
                              will be loaded (if possible).
    :param flask_config_dict: A dict used to update the Flask config (applied after
                              flask_config_file was loaded, if given).
    :param moin_config_class: If given, this class is instantiated as app.cfg;
                              otherwise, MOINCFG from the Flask config is used. If that
                              is also not present, the built-in DefaultConfig will be used.
    :param warn_default: Emit a warning if Moin falls back to its built-in default
                         config (perhaps the user forgot to specify MOINCFG?).
    :param kwargs: Additional keyword args will be patched into the Moin configuration
                   class (before its instance is created).
    """
    clock = Clock()
    clock.start("create_app total")
    logging.debug("running create_app_ext")
    app = Flask("moin")
    app.url_map.strict_slashes = False  # see issue 1737

    c = get_current_context(silent=True)
    info_name = getattr(c, "info_name", "")
    if getattr(c, "command", False):
        cmd_name = getattr(c.command, "name", "")
    else:
        cmd_name = ""
    logging.debug("info_name: %s cmd_name: %s", info_name, cmd_name)
    # Help doesn't need config or backend and should run independently of a valid wiki instance
    # moin --help results in info_name=moin and cmd_name=cli
    if (info_name == "moin" and cmd_name == "cli") or info_name == "help":
        return app

    clock.start("create_app load config")
    if flask_config_file:
        app.config.from_pyfile(path.abspath(flask_config_file))
    else:
        if not app.config.from_envvar("MOINCFG", silent=True):
            # no MOINCFG env variable set, try stuff in cwd:
            flask_config_file = path.abspath("wikiconfig_local.py")
            if not path.exists(flask_config_file):
                flask_config_file = path.abspath("wikiconfig.py")
                if not path.exists(flask_config_file):
                    if info_name == "create-instance":  # moin CLI
                        config_path = path.dirname(config.__file__)
                        flask_config_file = path.join(config_path, "wikiconfig.py")
                    else:
                        flask_config_file = None
            if flask_config_file:
                app.config.from_pyfile(path.abspath(flask_config_file))
    if flask_config_dict:
        app.config.update(flask_config_dict)
    Config = moin_config_class
    if not Config:
        Config = app.config.get("MOINCFG")
    if not Config:
        if warn_default:
            logging.warning("using builtin default configuration")
        from moin.config.default import DefaultConfig as Config
    for key, value in kwargs.items():
        setattr(Config, key, value)
    if Config.secrets is None:
        # reuse the secret configured for flask (which is required for sessions)
        Config.secrets = app.config.get("SECRET_KEY")
    app.cfg = Config()
    clock.stop("create_app load config")
    clock.start("create_app register")
    # register converters
    from werkzeug.routing import PathConverter

    class ItemNameConverter(PathConverter):
        """Like the default :class:`UnicodeConverter`, but it also matches
        slashes (except at the beginning AND end).
        This is useful for wikis and similar applications::

            Rule('/<itemname:wikipage>')
            Rule('/<itemname:wikipage>/edit')
        """

        regex = "[^/]+?(/[^/]+?)*"
        weight = 200

    app.url_map.converters["itemname"] = ItemNameConverter

    # register before/after request functions
    app.before_request(before_wiki)
    app.teardown_request(teardown_wiki)
    from moin.apps.frontend import frontend

    app.register_blueprint(frontend)
    from moin.apps.admin import admin

    app.register_blueprint(admin, url_prefix="/+admin")
    from moin.apps.feed import feed

    app.register_blueprint(feed, url_prefix="/+feed")
    from moin.apps.misc import misc

    app.register_blueprint(misc, url_prefix="/+misc")
    from moin.apps.serve import serve

    app.register_blueprint(serve, url_prefix="/+serve")

    # Create WikiLink analyzer after having registered all routes
    app.link_analyzer = WikiLinkAnalyzer(app)

    clock.stop("create_app register")
    clock.start("create_app flask-cache")
    # 'SimpleCache' caching uses a dict and is not thread safe according to the docs.
    cache = Cache(config={"CACHE_TYPE": "SimpleCache"})
    cache.init_app(app)
    app.cache = cache
    clock.stop("create_app flask-cache")
    # Initialize storage
    clock.start("create_app init backends")
    # start init_backends
    _init_backends(app, info_name, clock)
    clock.stop("create_app init backends")
    clock.start("create_app flask-babel")
    i18n_init(app)
    clock.stop("create_app flask-babel")
    # configure templates
    clock.start("create_app flask-theme")
    setup_themes(app)
    if app.cfg.template_dirs:
        app.jinja_env.loader = ChoiceLoader([FileSystemLoader(app.cfg.template_dirs), app.jinja_env.loader])
    app.register_error_handler(403, themed_error)
    app.context_processor(inject_common_template_vars)
    app.cfg.custom_css_path = os.path.isfile("wiki_local/custom.css")
    setup_jinja_env(app.jinja_env)
    clock.stop("create_app flask-theme")
    # Create a global counter to limit Content Security Policy reports and prevent spam
    app.csp_count = 0
    app.csp_last_date = ""
    clock.stop("create_app total")
    del clock
    return app


def destroy_app(app):
    deinit_backends(app)


def _init_backends(app, info_name, clock):
    """
    initialize the backends with exception handling
    """
    try:
        init_backends(app)
    except EmptyIndexError:
        # create-instance has no index at start and index-* subcommands check the index individually
        if info_name not in ["create-instance", "build-instance"] and not info_name.startswith("index-"):
            missing_indexes = app.storage.missing_index_check()
            if missing_indexes == "all":
                logging.error(
                    "Error: all wiki indexes missing. Try 'moin help' or 'moin --help' to get further information."
                )
            elif missing_indexes == "'latest_meta'":  # TODO: remove this check after 6-12 month
                logging.error(
                    "Error: Wiki index 'latest_meta' missing. Please see https://github.com/moinwiki/moin/pull/1877"
                )
            else:
                logging.error(f"Error: Wiki index {missing_indexes} missing, please check.")
            clock.stop("create_app init backends")
            clock.stop("create_app total")
            raise SystemExit(1)
        logging.debug("Wiki index not found.")


def init_backends(app, create_backend=False):
    """
    initialize the backends
    """
    # A ns_mapping consists of several lines, where each line is made up like this:
    # mountpoint, unprotected backend
    # Just initialize with unprotected backends.
    logging.debug("running init_backends")
    app.router = routing.Backend(app.cfg.namespace_mapping, app.cfg.backend_mapping)
    if create_backend or getattr(app.cfg, "create_backend", False):
        app.router.create()
    app.router.open()
    app.storage = indexing.IndexingMiddleware(
        app.cfg.index_storage,
        app.router,
        wiki_name=app.cfg.interwikiname,
        acl_rights_contents=app.cfg.acl_rights_contents,
    )

    logging.debug("create_backend: %s ", str(create_backend))
    if create_backend or getattr(app.cfg, "create_backend", False):  # 2. call of init_backends
        app.storage.create()
    app.storage.open()


def deinit_backends(app):
    app.storage.close()
    app.router.close()
    if app.cfg.destroy_backend:
        app.storage.destroy()
        app.router.destroy()


def setup_user() -> user.User:
    """
    Try to retrieve a valid user object from the request, be it
    either through the session or through a login.
    """
    logging.debug("running setup_user")
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
    if "login_submit" in form:
        # this is a real form, submitted by POST
        userobj = auth.handle_login(userobj, **form)
    elif "logout_submit" in form:
        # currently just a GET link
        userobj = auth.handle_logout(userobj)
    else:
        userobj = auth.handle_request(userobj)

    # if we still have no user obj, create a dummy:
    if not userobj:
        userobj = user.User(name=ANON, auth_method="invalid")
    # if we have a valid user we store it in the session
    if userobj.valid:
        session["user.itemid"] = userobj.itemid
        session["user.trusted"] = userobj.trusted
        session["user.auth_method"] = userobj.auth_method
        session["user.auth_attribs"] = userobj.auth_attribs
        session["user.session_token"] = userobj.get_session_token()
    return userobj


def setup_user_anon():
    """Setup anonymous user when no request available - CLI"""
    flaskg.user = user.User(name=ANON, auth_method="invalid")


def inject_common_template_vars() -> dict[str, Any]:
    if getattr(flaskg, "no_variable_injection", False):
        return {}
    else:
        return {
            "clock": flaskg.clock,
            "storage": flaskg.storage,
            "user": flaskg.user,
            "item_name": request.view_args.get("item_name", ""),
            "theme_supp": ThemeSupport(app.cfg),
            "cfg": app.cfg,
            "gen": make_generator(),
            "search_form": SearchForm.from_defaults(),
        }


def before_wiki():
    """
    Setup environment for wiki requests, start timers.
    """
    request_path = getattr(request, "path", "") if request else ""
    if is_static_content(request_path) or request_path == "/+cspreport/log":
        logging.debug(f"skipping variable injection in before_wiki for {request.path}")
        setattr(flaskg, "no_variable_injection", True)
        return

    logging.debug("running before_wiki")

    clock = flaskg.clock = Clock()
    clock.start("total")
    clock.start("init")
    try:
        flaskg.unprotected_storage = app.storage
        cli_no_request_ctx = False
        try:
            flaskg.user = setup_user()
        except RuntimeError:  # CLI call has no valid request context, create dummy
            flaskg.user = user.User(name=ANON, auth_method="invalid")
            cli_no_request_ctx = True

        flaskg.storage = protecting.ProtectingMiddleware(app.storage, flaskg.user, app.cfg.acl_mapping)

        flaskg.dicts = app.cfg.dicts()
        flaskg.groups = app.cfg.groups()

        if cli_no_request_ctx:  # no request.user_agent if this is pytest or cli
            flaskg.add_lineno_attr = False
        else:
            flaskg.add_lineno_attr = request.headers.get("User-Agent", None) and flaskg.user.edit_on_doubleclick
    finally:
        clock.stop("init")


def teardown_wiki(response):
    """
    Teardown environment of wiki requests, stop timers.
    """
    request_path = getattr(request, "path", "")
    if is_static_content(request_path) or request_path == "/+cspreport/log":
        return response

    logging.debug("running teardown_wiki")

    if edit_utils := getattr(flaskg, "edit_utils", None):
        # if transaction fails with sql file locked, we try to free it here
        try:
            edit_utils.conn.close()
        except AttributeError:
            pass

    try:
        # whoosh cache performance
        storage = flaskg.storage
        for cache in (storage.parse_acl, storage.eval_acl, storage.get_acls, storage.allows):
            if cache.cache_info()[3] > 0:
                msg = "cache = %s: hits = %s, misses = %s, maxsize = %s, size = %s" % (
                    (cache.__name__,) + cache.cache_info()
                )
                logging.debug(msg)
    except AttributeError:
        # moin commands may not have flaskg.storage
        pass

    try:
        clock = flaskg.pop("clock", None)
        if clock is not None:
            clock.stop("total", comment=request_path)
            del clock
    except AttributeError:
        # can happen if teardown_wiki() is called twice, e.g. by unit tests.
        pass

    return response


def is_static_content(request_path):
    """
    Check if content is static and does not need usual wiki handling
    """

    if request_path.startswith(("/static/", "/+serve/", "/+template/", "/_themes/")):
        return True
    else:
        return False
