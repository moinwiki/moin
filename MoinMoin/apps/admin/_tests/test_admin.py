# Copyright: 2011 Sam Toyer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details

"""
    MoinMoin - admin view tests
"""

from flask import url_for

class TestAdmin(object):
    def _test_view_get(self, viewname, status='200 OK', data=['<html>', '</html>'], viewopts={}):
        with self.app.test_client() as c:
            rv = c.get(url_for(viewname, **viewopts))
            assert rv.status == status
            assert rv.headers['Content-Type'] == 'text/html; charset=utf-8'
            for item in data: assert item in rv.data

    def test_index(self):
        self._test_view_get('admin.index')

    def test_userprofile(self):
        self._test_view_get('admin.userprofile', status='403 FORBIDDEN', viewopts=dict(user_name='DoesntExist'))

    def test_wikiconfig(self):
        self._test_view_get('admin.wikiconfig', status='403 FORBIDDEN')

    def test_wikiconfighelp(self):
        self._test_view_get('admin.wikiconfighelp', status='403 FORBIDDEN')

    def test_interwikihelp(self):
        self._test_view_get('admin.interwikihelp')

    def test_highlighterhelp(self):
        self._test_view_get('admin.highlighterhelp')

    def test_itemsize(self):
        self._test_view_get('admin.itemsize')

