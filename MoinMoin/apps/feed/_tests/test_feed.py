# Copyright: 2010,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - basic tests for feeds
"""

from MoinMoin._tests import wikiconfig

from MoinMoin.items import Item
from MoinMoin.config import CONTENTTYPE

class TestFeeds(object):
    class Config(wikiconfig.Config):
        """
        we just have this so the test framework creates a new app with empty backends for us.
        """

    def test_global_atom(self):
        with self.app.test_client() as c:
            rv = c.get('/+feed/atom')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'application/atom+xml'
            assert rv.data.startswith('<?xml')
            assert '<feed xmlns="http://www.w3.org/2005/Atom">' in rv.data
            assert '</feed>' in rv.data

    def test_global_atom_with_an_item(self):
        basename = u'Bar'
        item = Item.create(basename)
        item._save({CONTENTTYPE: u'text/plain;charset=utf-8'}, "foo data for feed item")
        with self.app.test_client() as c:
            rv = c.get('/+feed/atom')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'application/atom+xml'
            assert rv.data.startswith('<?xml')
            assert "foo data for feed item" in rv.data
