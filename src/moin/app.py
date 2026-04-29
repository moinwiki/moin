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

from typing import Any, TYPE_CHECKING

import logging
import os
import sys

from os import path, PathLike

import flask.ctx

from click import get_current_context

from flask import Flask, request, session

from flask_caching import Cache
from flask_theme import setup_themes

from jinja2 import ChoiceLoader, FileSystemLoader
from whoosh.index import EmptyIndexError

from moin import auth, user, config, log
from moin.config import WikiConfigProtocol
from moin.config.default import DefaultConfig
from moin.constants.misc import ANON
from moin.error import ConfigurationError
from moin.apps.frontend.views import bad_request
from moin.i18n import i18n_init
from moin.search import SearchForm
from moin.security.csp import set_csp_nonce
from moin.storage.middleware import protecting, indexing, routing
from moin.themes import setup_jinja_env, themed_error, ThemeSupport
from moin.utils import get_xstatic_module_path_map
from moin.utils import monkeypatch  # noqa
from moin.utils.clock import Clock
from moin.utils.forms import make_generator
from moin.wikiutil import WikiLinkAnalyzer

logger = log.getLogger(__name__)


if os.getcwd() not in sys.path and "" not in sys.path:
    # required in cases where wikiconfig_local.py imports wikiconfig_editme.py, see #698
    sys.path.append(os.getcwd())


class MoinApp(Flask):

    def __init__(
        self,
        flask_config_file: str | PathLike[str] | None = None,
        flask_config_dict: dict[str, Any] | None = None,
        moin_config_class: type | None = None,
        warn_default: bool = True,
        **kwargs: Any,
    ) -> None:
        clock = Clock()
        clock.start("create_app total")

        super().__init__("moin")
        self.url_map.strict_slashes = False  # see issue 1737

        info_name = self.get_info_name()
        cmd_name = self.get_command_name()
        logger.debug("info_name: %s cmd_name: %s", info_name, cmd_name)
        # Help doesn't need config or backend and should run independently of a valid wiki instance
        # moin --help results in info_name=moin and cmd_name=cli
        if (info_name == "moin" and cmd_name == "cli") or info_name == "help":
            return

        # if we have a config class, determine the configuration directory
        if not (config_dir := getattr(moin_config_class, "wikiconfig_dir", None)):
            config_dir = os.getcwd()

        with clock.timeit("create_app load config"):
            self.configure_flask(info_name, config_dir, flask_config_file, flask_config_dict)
            self.load_moin_config(moin_config_class, warn_default, **kwargs)

        with clock.timeit("create_app register"):
            self.register()

        # create wiki link analyzer after having registered all routes
        self.link_analyzer = WikiLinkAnalyzer(self)

        self.register_error_handler(400, bad_request)

        with clock.timeit("create_app flask-cache"):
            self.create_flask_cache()

        # init backends (routing, storage)
        with clock.timeit("create_app init backends"):
            self.init_backends()

        with clock.timeit("create_app flask-babel"):
            i18n_init(self)

        # configure templates
        with clock.timeit("create_app flask-theme"):
            setup_themes(self)
            if self.cfg.template_dirs:
                self.jinja_env.loader = ChoiceLoader([FileSystemLoader(self.cfg.template_dirs), self.jinja_env.loader])
            self.register_error_handler(403, themed_error)
            self.context_processor(inject_common_template_vars)
            self.cfg.custom_css_path = os.path.isfile("wiki_local/custom.css")
            setup_jinja_env(self.jinja_env)

        # create global counter to limit content security policy reports, prevent spam
        self.csp_count: int = 0
        self.csp_last_date: str = ""

        clock.stop("create_app total")
        del clock

    def get_info_name(self) -> str:
        c = get_current_context(silent=True)
        info_name = getattr(c, "info_name", "")
        return info_name

    def get_command_name(self) -> str:
        c = get_current_context(silent=True)
        if getattr(c, "command", False):
            cmd_name = getattr(c.command, "name", "")
        else:
            cmd_name = ""
        return cmd_name

    def configure_flask(
        self,
        info_name: str,
        wikiconfig_dir: str,
        flask_config_file: str | PathLike[str] | None = None,
        flask_config_dict: dict[str, Any] | None = None,
    ) -> None:
        if flask_config_file:
            self.config.from_pyfile(path.abspath(flask_config_file))
        elif not self.config.from_envvar("MOINCFG", silent=True):
            # no MOINCFG env variable set, try stuff in wikiconfig_dir:
            flask_config_file = path.join(wikiconfig_dir, "wikiconfig_local.py")
            if not path.exists(flask_config_file):
                flask_config_file = path.join(wikiconfig_dir, "wikiconfig.py")
                if not path.exists(flask_config_file):
                    if info_name == "create-instance":  # moin CLI
                        wikiconfig_dir = path.dirname(config.__file__)
                        flask_config_file = path.join(wikiconfig_dir, "wikiconfig.py")
                    else:
                        flask_config_file = None
            if flask_config_file:
                self.config.from_pyfile(path.abspath(flask_config_file))

        if flask_config_dict:
            self.config.update(flask_config_dict)

    def load_moin_config(self, moin_config_class: type | None = None, warn_default: bool = True, **kwargs: Any) -> None:

        if not moin_config_class:
            moin_config_class = self.config.get("MOINCFG")

        if not moin_config_class:
            if warn_default:
                logger.warning("using builtin default configuration")
            moin_config_class = DefaultConfig

        for key, value in kwargs.items():
            setattr(moin_config_class, key, value)

        if getattr(moin_config_class, "secrets", None) is None:
            # reuse the secret configured for flask (which is required for sessions)
            setattr(moin_config_class, "secrets", self.config.get("SECRET_KEY"))

        cfg = moin_config_class()
        if not isinstance(cfg, WikiConfigProtocol):
            raise ConfigurationError("Configuration does not implement WikiConfigProtocol")

        cfg.custom_css_path = os.path.isfile(os.path.join(cfg.wiki_local_dir, "custom.css"))

        cfg.serve_files.update(get_xstatic_module_path_map(cfg.mod_names))

        self.cfg = cfg

    def register(self) -> None:
        # register converters
        from werkzeug.routing import PathConverter

        class ItemNameConverter(PathConverter):
            """
            Like the default :class:`UnicodeConverter`, but it also matches
            slashes (except at the beginning AND end).
            This is useful for wikis and similar applications::

                Rule('/<itemname:wikipage>')
                Rule('/<itemname:wikipage>/edit')
            """

            regex = "[^/]+?(/[^/]+?)*"
            weight = 200

        self.url_map.converters["itemname"] = ItemNameConverter

        # register before/after request functions
        self.before_request(before_wiki)
        self.teardown_request(teardown_wiki)

        from moin.apps import admin, feed, frontend, misc, serve

        self.register_blueprint(frontend)
        self.register_blueprint(admin, url_prefix="/+admin")
        self.register_blueprint(feed, url_prefix="/+feed")
        self.register_blueprint(misc, url_prefix="/+misc")
        self.register_blueprint(serve, url_prefix="/+serve")

    def create_flask_cache(self) -> None:
        # 'SimpleCache' caching uses a dict and is not thread safe according to the docs.
        cache = Cache(config={"CACHE_TYPE": "SimpleCache"})
        cache.init_app(self)
        self.cache = cache

    def init_backends(self, create_backend: bool = False) -> None:
        """
        Initialize the backends with exception handling.
        """
        try:
            self._init_backends(create_backend)
        except EmptyIndexError:
            # create-instance has no index at start and index-* subcommands check the index individually
            info_name = self.get_info_name()
            if info_name not in ["create-instance", "build-instance"] and not info_name.startswith("index-"):
                missing_indexes = self.storage.missing_index_check()
                if missing_indexes == "all":
                    logger.error(
                        "Error: all wiki indexes missing. Try 'moin help' or 'moin --help' to get further information."
                    )
                elif missing_indexes == "'latest_meta'":  # TODO: remove this check after 6-12 month
                    logger.error(
                        "Error: Wiki index 'latest_meta' missing. Please see https://github.com/moinwiki/moin/pull/1877"
                    )
                else:
                    logger.error(f"Error: Wiki index {missing_indexes} missing, please check.")
                raise SystemExit(1)
            logger.debug("Wiki index not found.")

    def _init_backends(self, create_backend: bool) -> None:
        """
        Initialize the backends.
        """
        # A ns_mapping consists of several lines, where each line is made up like this:
        # mountpoint, unprotected backend
        # Just initialize with unprotected backends.
        logger.debug("running init_backends")
        self.router = routing.Backend(self.cfg.namespace_mapping, self.cfg.backend_mapping)
        if create_backend or getattr(self.cfg, "create_backend", False):
            self.router.create()
        self.router.open()
        self.storage = indexing.IndexingMiddleware(
            self.cfg.index_storage,
            self.router,
            wiki_name=self.cfg.interwikiname,
            acl_rights_contents=self.cfg.acl_rights_contents,
        )

        logger.debug("create_backend: %s ", str(create_backend))
        if create_backend or getattr(self.cfg, "create_backend", False):  # 2. call of init_backends
            self.storage.create()
        self.storage.open()

    def deinit_backends(self) -> None:
        self.storage.close()
        self.router.close()
        if self.cfg.destroy_backend:
            self.storage.destroy()
            self.router.destroy()


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
    :param moin_config_class: If given, this class is instantiated as current_app.cfg;
                              otherwise, MOINCFG from the Flask config is used. If that
                              is also not present, the built-in DefaultConfig will be used.
    :param warn_default: Emit a warning if Moin falls back to its built-in default
                         config (perhaps the user forgot to specify MOINCFG?).
    :param kwargs: Additional keyword args will be patched into the Moin configuration
                   class (before its instance is created).
    """
    logger.debug("running create_app_ext")
    return MoinApp(
        flask_config_file=flask_config_file,
        flask_config_dict=flask_config_dict,
        moin_config_class=moin_config_class,
        warn_default=warn_default,
        **kwargs,
    )


if TYPE_CHECKING:
    from moin.utils.edit_locking import Edit_Utils
    from moin.datastructures.backends import BaseDictsBackend, BaseGroupsBackend
    from moin.storage.middleware.indexing import IndexingMiddleware


class AppCtxGlobals(flask.ctx._AppCtxGlobals):
    link_analyzer: WikiLinkAnalyzer
    storage: protecting.ProtectingMiddleware
    unprotected_storage: IndexingMiddleware
    user: user.User
    dicts: BaseDictsBackend
    groups: BaseGroupsBackend
    add_lineno_attr: bool
    edit_utils: Edit_Utils
    clock: Clock
    _login_multistage: Any | None
    _login_multistage_name: Any | None
    _login_messages: list


def destroy_app(app: MoinApp):
    app.deinit_backends()


from . import current_app, flaskg  # pylint: disable=wrong-import-position


def setup_user() -> user.User:
    """
    Try to retrieve a valid user object from the request, be it
    either through the session or through a login.
    """
    logger.debug("running setup_user")
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
    """
    Setup anonymous user when no request available - CLI
    """
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
            "theme_supp": ThemeSupport(current_app.cfg),
            "cfg": current_app.cfg,
            "gen": make_generator(),
            "search_form": SearchForm.from_defaults(),
        }


def before_wiki():
    """
    Setup environment for wiki requests, start timers.
    """
    request_path = getattr(request, "path", "") if request else ""
    if is_static_content(request_path) or request_path == "/+cspreport/log":
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"skipping variable injection in before_wiki for {request.path}")
        setattr(flaskg, "no_variable_injection", True)
        return

    logger.debug("running before_wiki")

    clock = flaskg.clock = Clock()
    clock.start("total")
    clock.start("init")
    try:
        flaskg.unprotected_storage = current_app.storage
        cli_no_request_ctx = False
        try:
            flaskg.user = setup_user()
            set_csp_nonce(request)
        except RuntimeError:  # CLI call has no valid request context, create dummy
            flaskg.user = user.User(name=ANON, auth_method="invalid")
            cli_no_request_ctx = True

        flaskg.storage = protecting.ProtectingMiddleware(current_app.storage, flaskg.user, current_app.cfg.acl_mapping)

        flaskg.dicts = current_app.cfg.dicts()
        flaskg.groups = current_app.cfg.groups()

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

    logger.debug("running teardown_wiki")

    if edit_utils := getattr(flaskg, "edit_utils", None):
        # if transaction fails with sql file locked, we try to free it here
        try:
            edit_utils.conn.close()
        except AttributeError:
            pass

    if logger.isEnabledFor(logging.DEBUG):
        try:
            # whoosh cache performance
            storage = flaskg.storage
            for cache in (storage.parse_acl, storage.eval_acl, storage.get_acls, storage.allows):
                if cache.cache_info()[3] > 0:
                    msg = "cache = %s: hits = %s, misses = %s, maxsize = %s, size = %s" % (
                        (cache.__name__,) + cache.cache_info()
                    )
                    logger.debug(msg)
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


def is_static_content(request_path: str) -> bool:
    """
    Check if content is static and does not need usual wiki handling
    """
    return request_path.startswith(("/static/", "/+serve/", "/+template/", "/_themes/"))
