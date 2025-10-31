# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Tests for i18n
"""

import pytest

import flask_babel as babel

from flask import Flask
from flask_babel import Babel, force_locale

from moin.i18n import get_locale, get_timezone
from moin.i18n import _, L_, N_


@pytest.mark.usefixtures("_req_ctx")
def test_user_attributes():
    test_locale = get_locale()
    assert test_locale == "en"

    test_timezone = get_timezone()
    assert test_timezone == "UTC"


@pytest.mark.usefixtures("_app_ctx")
def test_text():
    # Test gettext
    result = _("test_text")
    assert result == "test_text"

    # Test lazy_gettext
    result = L_("test_lazy_text")
    assert result == "test_lazy_text"

    # Test ngettext
    result1 = N_("text1", "text2", 1)
    assert result1 == "text1"
    result2 = N_("text1", "text2", 2)
    assert result2 == "text2"


@pytest.fixture
def flask_app_with_de_locale():

    def select_locale():
        return "de_DE"

    app = Flask(__name__)
    Babel(app, locale_selector=select_locale)

    with app.test_request_context():
        yield app


@pytest.mark.usefixtures("flask_app_with_de_locale")
def test_force_locale():
    assert str(babel.get_locale()) == "de_DE"
    with force_locale("en_US"):
        assert str(babel.get_locale()) == "en_US"
    assert str(babel.get_locale()) == "de_DE"
