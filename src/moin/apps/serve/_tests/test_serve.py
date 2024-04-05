# Copyright: 2011 Sam Toyer
# License: GNU GPL V2 (or any later version), see LICENSE.txt for details

"""
    MoinMoin - tests for "serve" app
"""

from flask import url_for


class TestServe:
    def test_index(self, app):
        with app.test_client() as c:
            rv = c.get(url_for("serve.index"))
            assert rv.status == "200 OK"
            assert rv.headers["Content-Type"] == "text/plain"

    def test_files(self, app):
        with app.test_client() as c:
            rv = c.get(url_for("serve.files", name="DoesntExist"))
            assert rv.status == "404 NOT FOUND"
            assert rv.headers["Content-Type"] == "text/html; charset=utf-8"
            # TODO: remove workaround when Werkzeug >= 2.1.2 is set (PR 1325)
            assert "<!doctype html" in str(rv.data).lower()
