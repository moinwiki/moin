# Copyright: 2010,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - basic tests for feeds
"""

from MoinMoin._tests import wikiconfig


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

