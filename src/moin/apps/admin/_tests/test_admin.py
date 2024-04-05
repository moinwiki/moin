# Copyright: 2011 Sam Toyer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details

"""
    MoinMoin - admin view tests
"""

from flask import url_for

import pytest


@pytest.mark.parametrize(
    "url_for_args,status,data",
    (
        ({"endpoint": "admin.register_new_user"}, "403 FORBIDDEN", ("<html>", "</html>")),
        ({"endpoint": "admin.index"}, "403 FORBIDDEN", ("<html>", "</html>")),
        ({"endpoint": "admin.userprofile", "user_name": "DoesntExist"}, "403 FORBIDDEN", ("<html>", "</html>")),
        ({"endpoint": "admin.wikiconfig"}, "403 FORBIDDEN", ("<html>", "</html>")),
        ({"endpoint": "admin.wikiconfighelp"}, "403 FORBIDDEN", ("<html>", "</html>")),
        ({"endpoint": "admin.interwikihelp"}, "200 OK", ("<html>", "</html>")),
        ({"endpoint": "admin.highlighterhelp"}, "200 OK", ("<html>", "</html>")),
        ({"endpoint": "admin.itemsize"}, "200 OK", ("<html>", "</html>")),
    ),
)
def test_admin(app, url_for_args, status, data):
    with app.test_client() as c:
        rv = c.get(url_for(**url_for_args))
        assert rv.status == status
        assert rv.headers["Content-Type"] == "text/html; charset=utf-8"
        for item in data:
            assert item.encode() in rv.data
