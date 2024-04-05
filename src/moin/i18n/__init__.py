# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - i18n (internationalization) and l10n (localization) support

To use this, please use exactly this line (no less, no more)::

    from moin.i18n import _, L_, N_

    # _ == gettext
    # N_ == ngettext
    # L_ == lazy_gettext
"""


from babel import Locale
from contextlib import contextmanager

from flask import current_app, request
from flask import g as flaskg
from flask_babel import Babel, gettext, ngettext, lazy_gettext
from flask.globals import request_ctx

from moin import log

logging = log.getLogger(__name__)


_ = gettext
N_ = ngettext
L_ = lazy_gettext


def i18n_init(app):
    """initialize Flask-Babel"""
    Babel(app, locale_selector=get_locale, timezone_selector=get_timezone)


def get_locale():
    """return the locale for the current user"""
    locale = None
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, "user", None)
    if u and u.locale is not None:
        # locale is given in user profile, use it
        locale = u.locale
        logging.debug(f"user locale = {locale!r}")
    else:
        # try to guess the language from the user accept
        # header the browser transmits. The best match wins.
        cli_no_request_ctx = False
        try:
            logging.debug(f"request.accept_languages = {request.accept_languages!r}")
        except RuntimeError:  # CLI call has no valid request context
            cli_no_request_ctx = True

        supported_locales = [Locale("en")] + current_app.extensions["babel"].instance.list_translations()
        logging.debug(f"supported_locales = {supported_locales!r}")
        supported_languages = [str(locale) for locale in supported_locales]
        logging.debug(f"supported_languages = {supported_languages!r}")
        if not cli_no_request_ctx:
            locale = request.accept_languages.best_match(supported_languages, "en")
            logging.debug(f"best match locale = {locale!r}")
    if not locale:
        locale = current_app.cfg.locale_default
        logging.debug(f"default locale = {locale!r}")
    return locale


def get_timezone():
    """return the timezone for the current user"""
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, "user", None)
    if u and u.timezone is not None:
        return u.timezone


# Original source is a patch to Flask Babel
# https://github.com/lalinsky/flask-babel/commit/09ee1702c7129598bb202aa40a0e2e19f5414c24
@contextmanager
def force_locale(locale):
    """Temporarily overrides the currently selected locale. Sometimes
    it is useful to switch the current locale to different one, do
    some tasks and then revert back to the original one. For example,
    if the user uses German on the web site, but you want to send
    them an email in English, you can use this function as a context
    manager::

        with force_locale('en_US'):
            send_email(gettext('Hello!'), ...)
    """
    ctx = request_ctx
    if ctx is None:
        yield
        return
    babel = ctx.app.extensions["babel"]
    orig_locale_selector = babel.locale_selector
    orig_attrs = {}
    for key in ("babel_translations", "babel_locale"):
        orig_attrs[key] = getattr(ctx, key, None)
    try:
        babel.locale_selector = lambda: locale
        for key in orig_attrs:
            setattr(ctx, key, None)
        yield
    finally:
        babel.locale_selector = orig_locale_selector
        for key, value in orig_attrs.items():
            setattr(ctx, key, value)
