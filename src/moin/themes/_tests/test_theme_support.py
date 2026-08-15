# Copyright: 2025 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import pytest

from moin import current_app, flaskg
from moin.themes import ThemeSupport, get_current_theme
from moin.user import User

from moin._tests import wikiconfig


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
    return ThemeSupport(current_app.cfg)


@pytest.mark.usefixtures("_req_ctx", "_test_user")
def test_get_user_home(_test_user, theme_supp):
    wiki_href, display_name, title, exists = theme_supp.userhome()
    assert wiki_href == "/users/lemmy"
    assert display_name == "lemmy"
    assert title == "lemmy @ Self"
    assert not exists


@pytest.mark.usefixtures("_req_ctx")
def test_get_current_theme_recovers_from_incomplete_registry():
    """
    Regression test: if flask_theme's ThemeManager.themes is incomplete
    (e.g. a race in its own refresh() during mass worker recycling on an
    httpd reload -- one thread's `self._themes = {}` can orphan another
    thread's in-progress population), get_current_theme()'s existing
    fallback retried the *same* lookup for the already-default theme and
    crashed identically with an unhandled KeyError. It should instead
    force a registry refresh and retry once more before giving up.
    """
    default_theme = current_app.cfg.theme_default
    assert default_theme in current_app.theme_manager.themes

    # simulate the race: the registry looks populated, but is missing
    # every entry, including the default theme's
    current_app.theme_manager._themes = {}

    theme = get_current_theme()
    assert theme.identifier == default_theme
    # the forced refresh should have restored the full registry, not
    # just papered over the one lookup
    assert default_theme in current_app.theme_manager.themes
