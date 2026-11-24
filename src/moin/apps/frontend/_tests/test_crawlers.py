# Copyright: 2026 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for what the frontend offers to crawlers (and what it answers them).
"""

from __future__ import annotations

import time

from urllib.robotparser import RobotFileParser

import pytest

from flask import url_for

from moin.apps._tests.utils import create_user, login, modify_item, make_modify_form_data
from moin.security import DefaultSecurityPolicy


def test_robots_txt_disallows_non_content_views(client):
    """
    The Disallow rules are path prefixes, so they must match the urls moin generates: e.g.
    "Disallow: /+index/" would not match the global index at /+index.
    """
    rv = client.get(url_for("frontend.robots"))
    assert rv.status_code == 200
    robots = RobotFileParser()
    robots.parse(rv.get_data(as_text=True).splitlines())
    disallowed = [
        url_for("frontend.index"),
        url_for("frontend.index", item_name="SomeItem"),
        url_for("frontend.wanted_items"),
        url_for("frontend.orphaned_items"),
        url_for("frontend.global_tags"),
        url_for("frontend.tagged_items", tag="SomeTag"),
        url_for("frontend.global_history"),
        url_for("frontend.history", item_name="SomeItem"),
        url_for("frontend.sitemap", item_name="SomeItem"),
        url_for("frontend.show_item", item_name="SomeItem", rev="0123456789abcdef0123456789abcdef"),
        url_for("frontend.show_item_meta", item_name="SomeItem"),
    ]
    assert [url for url in disallowed if robots.can_fetch("*", url)] == []
    assert robots.can_fetch("*", url_for("frontend.show_item", item_name="SomeItem"))
    assert robots.can_fetch("*", url_for("frontend.show_item", item_name="SomeItem/SubItem"))


@pytest.mark.parametrize(
    "name, far_away",
    [
        ("Calendar/2000-01-01", True),
        ("Calendar/99999-01-01", True),
        ("Calendar/" + "9" * 5000 + "-01-01", True),
        ("Calendar/THISYEAR-01-01", False),
        ("Calendar/01-01", False),  # anniversary calendar, no year
        ("SomeItem", False),
    ],
)
def test_far_away_day_items_are_cheap_404s(client, monkeypatch, name, far_away):
    """
    Crawlers request lots of nonexistent day items (BasePage/yyyy-mm-dd) with years far away
    from now. For users who may not create them, those get a short plain text 404, not a page.
    """
    name = name.replace("THISYEAR", str(time.gmtime().tm_year))
    monkeypatch.setattr(DefaultSecurityPolicy, "create", lambda self, itemname: False, raising=False)
    rv = client.get(url_for("frontend.show_item", item_name=name))
    assert rv.status_code == 404
    assert (rv.mimetype == "text/plain") == far_away


def test_far_away_day_items_for_creators(client, monkeypatch):
    """Users who may create a far away day item still get the create view."""
    monkeypatch.setattr(DefaultSecurityPolicy, "create", lambda self, itemname: True, raising=False)
    rv = client.get(url_for("frontend.show_item", item_name="Calendar/2000-01-01"))
    assert rv.status_code == 404
    assert rv.mimetype == "text/html"


def test_far_away_day_items_that_exist_are_shown(client):
    create_user("moin", "Xiwejr622")
    login(client, "moin", "Xiwejr622")
    modify_item(client, "Calendar/2000-01-01", make_modify_form_data("Calendar/2000-01-01", content="party\n"))
    client.get(url_for("frontend.logout", logout_submit=1))
    rv = client.get(url_for("frontend.show_item", item_name="Calendar/2000-01-01"))
    assert rv.status_code == 200
    assert b"party" in rv.data


def test_sitemap_and_similar_names_not_offered_to_anonymous(client):
    """The site map and similar names views are expensive, crawlers shall not find links to them."""
    create_user("moin", "Xiwejr622")
    login(client, "moin", "Xiwejr622")
    modify_item(client, "ViewsItem", make_modify_form_data("ViewsItem", content="hello\n"))
    sitemap_url = url_for("frontend.sitemap", item_name="ViewsItem")
    similar_url = url_for("frontend.similar_names", item_name="ViewsItem")
    rv = client.get(url_for("frontend.show_item", item_name="ViewsItem"))
    assert sitemap_url.encode() in rv.data
    assert similar_url.encode() in rv.data
    client.get(url_for("frontend.logout", logout_submit=1))
    rv = client.get(url_for("frontend.show_item", item_name="ViewsItem"))
    assert rv.status_code == 200
    assert sitemap_url.encode() not in rv.data
    assert similar_url.encode() not in rv.data
