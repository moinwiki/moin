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


def test_global_atom_with_a_renamed_item(client):
    """
    Regression test: the feed history loop looks up each historical
    revision by the name it had at that point in time. If the item has
    since been renamed, a name-based lookup for an old revision no longer
    resolves (the current item doesn't answer to that name any more), and
    used to crash rendering that entry instead of showing it.
    """

    create_user("moin", "Xiwejr622")

    login(client, "moin", "Xiwejr622")

    old_name = "OldName"
    new_name = "NewName"

    # two revisions before the rename: the second one has a parent revid,
    # which is what actually reaches the crashing diff-render code path
    # below (a revision with no parent takes a different, unaffected
    # rendering path).
    response = modify_item(client, old_name, make_modify_form_data(old_name, comment="first revision"))
    assert response.status_code == 302
    response = modify_item(client, old_name, make_modify_form_data(old_name, comment="before rename"))
    assert response.status_code == 302

    response = client.post(
        url_for("frontend.rename_item", item_name=old_name), data={"target": new_name, "comment": "renamed"}
    )
    assert response.status_code == 302

    rv = client.get(url_for("feed.atom"))
    assert rv.status_code == 200
    assert rv.headers["Content-Type"] == "application/atom+xml"
    assert "MoinMoin feels unhappy" not in rv.text


def test_global_atom_cache_is_per_user(client):
    # The feed body is ACL-filtered per reader, so the cache key must bind
    # the reader identity: without it, a cached admin feed (containing
    # private items) is served to an anonymous reader whose latest
    # readable rev is the same. SecretNote is created first and PublicNote
    # last, so both readers share the same latest revid and would collide
    # on a reader-blind key.
    create_user("feedadmin", "Feedpass123")
    login(client, "feedadmin", "Feedpass123")

    # ACLs are metadata, set through the modify form (the test client runs
    # inside the request context, so direct storage writes have no flaskg).
    response = modify_item(
        client,
        "SecretNote",
        make_modify_form_data("SecretNote", content="top secret content") | {"meta_form_acl": "feedadmin:read,write"},
    )
    assert response.status_code == 302
    response = modify_item(
        client,
        "PublicNote",
        make_modify_form_data("PublicNote", comment="public note for feed") | {"meta_form_acl": "All:read,write"},
    )
    assert response.status_code == 302

    # admin primes the cache: feed includes the private item
    rv = client.get(url_for("feed.atom"))
    assert rv.status_code == 200
    assert "SecretNote" in rv.text

    # anonymous reader must not get the cached admin feed: expire nothing,
    # just drop the session. The shared cache still holds the admin entry;
    # the anon request must miss it (reader-bound key) and regenerate.
    with client.session_transaction() as sess:
        sess.clear()
    rv = client.get(url_for("feed.atom"))
    assert rv.status_code == 200
    assert "SecretNote" not in rv.text
    assert "PublicNote" in rv.text
