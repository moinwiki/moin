# Copyright: 2010,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for feeds
"""

from __future__ import annotations

from flask import url_for

from moin.apps._tests.utils import create_user, login, modify_item, make_modify_form_data


def test_global_atom(client):
    rv = client.get(url_for("feed.atom"))
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "application/atom+xml"
    assert rv.text.startswith("<?xml")
    assert '<feed xmlns="http://www.w3.org/2005/Atom">' in rv.text
    assert "</feed>" in rv.text


def test_global_atom_with_an_item(client):

    create_user("moin", "Xiwejr622")

    login(client, "moin", "Xiwejr622")

    item_name = "Foo"

    response = modify_item(client, item_name, make_modify_form_data(item_name, comment="foo data for feed item"))
    assert response.status_code == 302

    rv = client.get(url_for("feed.atom"))
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "application/atom+xml"
    assert rv.text.startswith("<?xml")
    assert "foo data for feed item" in rv.text

    # Test cache invalidation
    response = modify_item(
        client, item_name, make_modify_form_data(item_name, comment="checking if the cache invalidation works")
    )

    rv = client.get(url_for("feed.atom"))
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "application/atom+xml"
    assert rv.text.startswith("<?xml")
    assert "checking if the cache invalidation works" in rv.text
