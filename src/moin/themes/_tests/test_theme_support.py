# Copyright: 2025 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import pytest

from flask import current_app as app
from flask import g as flaskg

from moin._tests import wikiconfig
from moin.themes import ThemeSupport
from moin.user import User


@pytest.fixture
def _test_user():
    orig_user = flaskg.user
    flaskg.user = User(name="lemmy")
    yield
    flaskg.user = orig_user


@pytest.fixture
def cfg():
    class Config(wikiconfig.Config):
        interwiki_map = dict(Self="http://localhost:8080/", MoinMoin="http://moinmo.in/")

    return Config


@pytest.fixture
def theme_supp():
    return ThemeSupport(app.cfg)


@pytest.mark.usefixtures("_req_ctx", "_test_user")
def test_get_user_home(_test_user, theme_supp):
    wiki_href, display_name, title, exists = theme_supp.userhome()
    assert wiki_href == "/users/lemmy"
    assert display_name == "lemmy"
    assert title == "lemmy @ Self"
    assert not exists
