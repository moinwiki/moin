# Copyright: 2010,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for misc views
"""

from flask import url_for


def test_global_sitemap(client):
    rv = client.get(url_for("misc.sitemap"))
    assert rv.status == "200 OK"
    assert rv.headers["Content-Type"] == "text/xml; charset=utf-8"
    assert rv.data.startswith(b"<?xml")
    assert b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in rv.data
    assert b"</urlset>" in rv.data


def test_urls_names(client):
    rv = client.get(url_for("misc.urls_names"))
    assert rv.status == "200 OK"
    assert rv.headers["Content-Type"] == "text/plain; charset=utf-8"
