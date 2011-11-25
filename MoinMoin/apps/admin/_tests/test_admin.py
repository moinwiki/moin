# Copyright: 2011 Sam Toyer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details

"""
    MoinMoin - admin view tests
"""

from flask import url_for

def pytest_generate_tests(metafunc):
    if 'view' in metafunc.funcargs:
        parameters = metafunc.cls.params[metafunc.func.__name__]
        argnames = parameters[0].keys()
        metafunc.parametrize(argnames, [[parameters[argument] for argument in argnames] for parameter in parameters])

class TestAdmin(object):
    superuser_views = ['admin.' + action for action in ['require_permission', 'sysitems_upgrade',
            'wikiconfig', 'wikiconfighelp',
            ]
        ]
    params = {
        'test_superuser_page': [dict(view=view) for view in superuser_views]
        }

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

    def test_superuser_page(self, view):
        # This will die for the reasons outlined in apps/frontend/_tests/test_frontend.py
        self._test_view_get(view, status='403 FORBIDDEN')

    def test_interwikihelp(self):
        self._test_view_get('admin.interwikihelp')

    def test_highlighterhelp(self):
        self._test_view_get('admin.highlighterhelp')

    def test_itemsize(self):
        self._test_view_get('admin.itemsize')

