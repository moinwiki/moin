# Copyright: 2011 Sam Toyer
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details

"""
MoinMoin - Tests for admin views
"""

import pytest

from flask import url_for

from moin._tests import wikiconfig
from moin.apps._tests.utils import create_user, login
from moin.constants.keys import ACL, CONTENTTYPE, TAGS, USERGROUP


@pytest.mark.parametrize(
    "url_for_args,status,data",
    (
        ({"endpoint": "admin.register_new_user"}, "403 FORBIDDEN", ("<html lang=", "</html>")),
        ({"endpoint": "admin.index"}, "403 FORBIDDEN", ("<html lang=", "</html>")),
        ({"endpoint": "admin.userprofile", "user_name": "DoesntExist"}, "403 FORBIDDEN", ("<html lang=", "</html>")),
        ({"endpoint": "admin.wikiconfig"}, "403 FORBIDDEN", ("<html lang=", "</html>")),
        ({"endpoint": "admin.wikiconfighelp"}, "403 FORBIDDEN", ("<html lang=", "</html>")),
        ({"endpoint": "admin.interwikihelp"}, "403 FORBIDDEN", ("<html lang=", "</html>")),
        ({"endpoint": "admin.highlighterhelp"}, "403 FORBIDDEN", ("<html lang=", "</html>")),
        ({"endpoint": "admin.itemsize"}, "403 FORBIDDEN", ("<html lang=", "</html>")),
    ),
)
def test_admin(client, url_for_args, status, data):
    rv = client.get(url_for(**url_for_args))
    assert rv.status == status
    assert rv.headers["Content-Type"] == "text/html; charset=utf-8"
    for item in data:
        assert item.encode() in rv.data


class TestUserBrowser:
    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            acl_functions = "AdminUser:superuser"

        return Config

    def test_userbrowser_escapes_html_in_group_name(self, client):
        from moin._tests import update_item

        create_user("AdminUser", "Xiwejr622")
        login(client, "AdminUser", "Xiwejr622")
        # any item name matching item_group_regex ("\S+Group") is a group name
        group_name = "<svg/onload=alert(document.domain)>XssGroup"
        update_item(group_name, {USERGROUP: ["AdminUser"]}, b"")

        response = client.get(url_for("admin.userbrowser"))
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "&lt;svg/onload=alert(document.domain)&gt;XssGroup" in html
        assert group_name not in html


class TestItemReports:
    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            acl_functions = "AdminUser:superuser"

        return Config

    def test_item_reports(self, client):
        from moin import user
        from moin._tests import update_item

        create_user("AdminUser", "Xiwejr622")
        login(client, "AdminUser", "Xiwejr622")
        moin_markup = {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}
        update_item("ReportBeta", {ACL: "ReportGroup:read All:read", TAGS: ["tag1"], **moin_markup}, "[[ReportWanted]]")
        update_item("ReportAlpha", {ACL: "ReportGroup:read All:read", **moin_markup}, "[[ReportBeta]]")
        update_item("ReportGamma/Sub", {TAGS: ["tag1", "tag2"], **moin_markup}, "x")

        def get(endpoint, **kw):
            response = client.get(url_for(endpoint, **kw))
            assert response.status_code == 200, endpoint
            return response.get_data(as_text=True)

        def assert_order(html, names):
            positions = [html.index(name) for name in names]
            assert positions == sorted(positions), html

        # the ACL reports list the items sorted by name
        assert_order(get("admin.item_acl_report"), ["ReportAlpha", "ReportBeta", "ReportGamma/Sub"])
        uid = user.User(name="AdminUser").itemid
        assert_order(get("admin.user_acl_report", uid=uid), ["ReportAlpha", "ReportBeta", "ReportGamma/Sub"])
        html = get("admin.group_acl_report", group_name="ReportGroup")
        assert_order(html, ["ReportAlpha", "ReportBeta"])
        assert "ReportGamma/Sub" not in html
        # these views do not depend on the order of their search results
        html = get("admin.itemsize")
        assert all(name in html for name in ["ReportAlpha", "ReportBeta", "ReportGamma/Sub"])
        html = get("frontend.orphaned_items")
        assert "ReportAlpha" in html and "ReportGamma/Sub" in html and "ReportBeta" not in html
        html = get("frontend.wanted_items")
        assert "ReportWanted" in html and "ReportAlpha" not in html
        html = get("frontend.global_tags")
        assert "tag1" in html and "tag2" in html
