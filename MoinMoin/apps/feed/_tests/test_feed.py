# Copyright: 2010,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - basic tests for feeds
"""

from flask import url_for

from MoinMoin.items import Item
from MoinMoin.config import CONTENTTYPE, COMMENT
from MoinMoin._tests import update_item, wikiconfig

class TestFeeds(object):
    class Config(wikiconfig.Config):
        """
        we just have this so the test framework creates a new app with empty backends for us.
        """

    def test_global_atom(self):
        with self.app.test_client() as c:
            rv = c.get(url_for('feed.atom'))
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'application/atom+xml'
            assert rv.data.startswith('<?xml')
            assert '<feed xmlns="http://www.w3.org/2005/Atom">' in rv.data
            assert '</feed>' in rv.data

    def test_global_atom_with_an_item(self):
        basename = u'Foo'
        item = update_item(basename, {COMMENT: u"foo data for feed item"}, '')
        with self.app.test_client() as c:
            rv = c.get(url_for('feed.atom'))
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'application/atom+xml'
            assert rv.data.startswith('<?xml')
            assert "foo data for feed item" in rv.data

        # tests the cache invalidation
        update_item(basename, {COMMENT: u"checking if the cache invalidation works"}, '')
        with self.app.test_client() as c:
            rv = c.get(url_for('feed.atom'))
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'application/atom+xml'
            assert rv.data.startswith('<?xml')
            assert "checking if the cache invalidation works" in rv.data

