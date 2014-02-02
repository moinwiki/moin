# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for i18n
"""

import pytest

from flask import Flask
from flask.ext import babel

from MoinMoin.i18n import get_locale, get_timezone, force_locale
from MoinMoin.i18n import _, L_, N_


def test_user_attributes():
    test_locale = get_locale()
    assert test_locale == 'en'

    test_timezone = get_timezone()
    assert test_timezone == 'UTC'


def test_text():
    # test for gettext
    result = _('test_text')
    assert result == 'test_text'

    # test for lazy_gettext
    result = L_('test_lazy_text')
    assert result == u'test_lazy_text'

    # test for ngettext
    result1 = N_('text1', 'text2', 1)
    assert result1 == 'text1'
    result2 = N_('text1', 'text2', 2)
    assert result2 == 'text2'


def test_force_locale():
    pytest.skip("This test needs to be run with --assert=reinterp or --assert=plain flag")
    app = Flask(__name__)
    b = babel.Babel(app)

    @b.localeselector
    def select_locale():
        return 'de_DE'

    with app.test_request_context():
        assert str(babel.get_locale()) == 'de_DE'
        with force_locale('en_US'):
            assert str(babel.get_locale()) == 'en_US'
        assert str(babel.get_locale()) == 'de_DE'
