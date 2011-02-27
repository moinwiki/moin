"""
    MoinMoin - basic tests for feeds

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

class TestFeeds(object):
    def test_global_atom(self):
        with self.app.test_client() as c:
            rv = c.get('/+feed/atom')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'application/atom+xml'
            assert rv.data.startswith('<?xml')
            assert '<feed xmlns="http://www.w3.org/2005/Atom">' in rv.data
            assert '</feed>' in rv.data

