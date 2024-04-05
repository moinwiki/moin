# Copyright: 2010,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - basic tests for feeds
"""

from flask import url_for

from moin.constants.keys import COMMENT
from moin._tests import update_item


class TestFeeds:
    def test_global_atom(self, app):
        with app.test_client() as c:
            rv = c.get(url_for("feed.atom"))
            assert rv.status == "200 OK"
            assert rv.headers["Content-Type"] == "application/atom+xml"
            assert rv.data.startswith(b"<?xml")
            assert b'<feed xmlns="http://www.w3.org/2005/Atom">' in rv.data
            assert b"</feed>" in rv.data

    def test_global_atom_with_an_item(self, app):
        basename = "Foo"
        update_item(basename, {COMMENT: "foo data for feed item"}, "")
        with app.test_client() as c:
            rv = c.get(url_for("feed.atom"))
            assert rv.status == "200 OK"
            assert rv.headers["Content-Type"] == "application/atom+xml"
            assert rv.data.startswith(b"<?xml")
            assert b"foo data for feed item" in rv.data

        # tests the cache invalidation
        update_item(basename, {COMMENT: "checking if the cache invalidation works"}, "")
        with app.test_client() as c:
            rv = c.get(url_for("feed.atom"))
            assert rv.status == "200 OK"
            assert rv.headers["Content-Type"] == "application/atom+xml"
            assert rv.data.startswith(b"<?xml")
            assert b"checking if the cache invalidation works" in rv.data
