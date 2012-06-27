# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - i18n (internationalization) and l10n (localization) support

To use this, please use exactly this line (no less, no more)::

    from MoinMoin.i18n import _, L_, N_

    # _ == gettext
    # N_ == ngettext
    # L_ == lazy_gettext
"""


from babel import Locale

from flask import current_app, request
from flask import g as flaskg
from flaskext.babel import Babel, gettext, ngettext, lazy_gettext

_ = gettext
N_ = ngettext
L_ = lazy_gettext

from MoinMoin import log
logging = log.getLogger(__name__)


def i18n_init(app):
    """ initialize Flask-Babel """
    babel = Babel(app)
    babel.localeselector(get_locale)
    babel.timezoneselector(get_timezone)


def get_locale():
    """ return the locale for the current user """
    locale = None
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, 'user', None)
    if u and u.locale is not None:
        # locale is given in user profile, use it
        locale = u.locale
        logging.debug("user locale = {0!r}".format(locale))
    else:
        # try to guess the language from the user accept
        # header the browser transmits. The best match wins.
        logging.debug("request.accept_languages = {0!r}".format(request.accept_languages))
        supported_locales = [Locale('en')] + current_app.babel_instance.list_translations()
        logging.debug("supported_locales = {0!r}".format(supported_locales))
        supported_languages = [str(l) for l in supported_locales]
        logging.debug("supported_languages = {0!r}".format(supported_languages))
        locale = request.accept_languages.best_match(supported_languages, 'en')
        logging.debug("best match locale = {0!r}".format(locale))
    if not locale:
        locale = current_app.cfg.locale_default
        logging.debug("default locale = {0!r}".format(locale))
    return locale


def get_timezone():
    """ return the timezone for the current user """
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, 'user', None)
    if u and u.timezone is not None:
        return u.timezone
