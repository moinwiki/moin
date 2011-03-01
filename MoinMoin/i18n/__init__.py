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


from flask import current_app, request, flaskg

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
    else:
        # try to guess the language from the user accept
        # header the browser transmits. The best match wins.
        supported_languages = ['de', 'fr', 'en'] # XXX
        locale = request.accept_languages.best_match(supported_languages)
    if not locale:
        locale = current_app.cfg.locale_default
    return locale


def get_timezone():
    """ return the timezone for the current user """
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, 'user', None)
    if u and u.timezone is not None:
        return u.timezone

