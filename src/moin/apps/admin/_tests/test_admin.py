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
from moin.constants.keys import USERGROUP


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
