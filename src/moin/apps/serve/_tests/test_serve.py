# Copyright: 2011 Sam Toyer
# License: GNU GPL V2 (or any later version), see LICENSE.txt for details

"""
MoinMoin - Tests for the serve app
"""

from flask import url_for


def test_index(client):
    rv = client.get(url_for("serve.index"))
    assert rv.status == "200 OK"
    assert rv.headers["Content-Type"] == "text/plain"


def test_files(client):
    rv = client.get(url_for("serve.files", name="DoesntExist"))
    assert rv.status == "404 NOT FOUND"
    assert rv.headers["Content-Type"] == "text/html; charset=utf-8"
    assert rv.text.startswith("<!doctype html")
