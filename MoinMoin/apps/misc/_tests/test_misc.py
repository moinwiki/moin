# Copyright: 2010,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - basic tests for misc views
"""

from MoinMoin._tests import wikiconfig


class TestMisc(object):
    class Config(wikiconfig.Config):
        """
        we just have this so the test framework creates a new app with empty backends for us.
        """

    def test_global_sitemap(self):
        with self.app.test_client() as c:
            rv = c.get('/+misc/sitemap')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/xml; charset=utf-8'
            assert rv.data.startswith('<?xml')
            assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in rv.data
            assert '</urlset>' in rv.data

    def test_urls_names(self):
        with self.app.test_client() as c:
            rv = c.get('/+misc/urls_names')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/plain; charset=utf-8'
