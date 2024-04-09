# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - basic tests for frontend
"""

from io import BytesIO

from flask import url_for
from flask import g as flaskg
from werkzeug.datastructures import FileStorage

from moin.apps.frontend import views
from moin import user

import pytest


class TestFrontend:

    @pytest.fixture(autouse=True)
    def custom_setup(self, app):
        self.app = app

    def _test_view(
        self,
        viewname,
        status="200 OK",
        data=("<html>", "</html>"),
        content_types=("text/html; charset=utf-8",),
        viewopts=None,
        params=None,
    ):
        if viewopts is None:
            viewopts = {}
        if params is None:
            params = {}

        with self.app.test_client() as c:
            for method in ["HEAD", "GET"]:
                print("%s %s" % (method, url_for(viewname, **viewopts)))
                rv = c.open(url_for(viewname, **viewopts), method=method, data=params)
                rv_data = rv.data.decode()
                assert rv.status == status
                assert rv.headers["Content-Type"] in content_types
                if method == "GET":
                    for item in data:
                        if item == "<!doctype html":  # TODO: remove workaround when Werkzeug >= 2.1.2 is set
                            assert item in str(rv_data).lower()
                        else:
                            assert item in rv_data
        return rv

    def _test_view_post(
        self,
        viewname,
        status="302 FOUND",
        content_types=("text/html; charset=utf-8",),
        data=("<html>", "</html>"),
        form=None,
        viewopts=None,
    ):
        if viewopts is None:
            viewopts = {}
        if form is None:
            form = {}
        print("POST %s" % url_for(viewname, **viewopts))
        with self.app.test_client() as c:
            rv = c.post(url_for(viewname, **viewopts), data=form)
            rv_data = rv.data.decode()
            assert rv.status == status
            assert rv.headers["Content-Type"] in content_types
            for item in data:
                assert item in rv_data
            return rv

    def test_ajaxdelete_item_name_route(self):
        self._test_view_post(
            "frontend.ajaxdelete",
            status="200 OK",
            content_types=["application/json"],
            data=["{", "}"],
            form=dict(comment="Test", itemnames='["DoesntExist"]'),
            viewopts=dict(item_name="DoesntExist"),
        )

    def test_ajaxdelete_no_item_name_route(self):
        self._test_view_post(
            "frontend.ajaxdelete",
            status="200 OK",
            content_types=["application/json"],
            data=["{", "}"],
            form=dict(comment="Test", itemnames='["DoesntExist"]'),
        )

    def test_ajaxdestroy_item_name_route(self):
        self._test_view_post(
            "frontend.ajaxdestroy",
            status="200 OK",
            content_types=["application/json"],
            data=["{", "}"],
            form=dict(comment="Test", itemnames='["DoesntExist"]'),
            viewopts=dict(item_name="DoesntExist"),
        )

    def test_ajaxdestroy_no_item_name_route(self):
        self._test_view_post(
            "frontend.ajaxdestroy",
            status="200 OK",
            content_types=["application/json"],
            data=["{", "}"],
            form=dict(comment="Test", itemnames='["DoesntExist"]'),
        )

    def test_ajaxmodify(self):
        self._test_view_post("frontend.ajaxmodify", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_jfu_server(self):
        self._test_view_post(
            "frontend.jfu_server",
            status="200 OK",
            content_types=["application/json"],
            data=["{", "}"],
            form=dict(
                file_storage=FileStorage(
                    BytesIO(b"Hello, world"),
                    filename="C:\\fakepath\\DoesntExist.txt",
                    content_type="text/plain; charset=utf-8",
                )
            ),
            viewopts=dict(item_name="WillBeCreated"),
        )

    def test_show_item(self):
        self._test_view("frontend.show_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_show_dom(self):
        self._test_view(
            "frontend.show_dom",
            status="404 NOT FOUND",
            data=["<?xml", ">"],
            viewopts=dict(item_name="DoesntExist"),
            content_types=["text/xml; charset=utf-8"],
        )

    def test_indexable(self):
        self._test_view("frontend.indexable", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_highlight_item(self):
        self._test_view("frontend.highlight_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_show_item_meta(self):
        self._test_view("frontend.show_item_meta", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_content_item(self):
        self._test_view("frontend.content_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_get_item(self):
        self._test_view("frontend.get_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_download_item(self):
        self._test_view("frontend.download_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_convert_item(self):
        self._test_view(
            "frontend.convert_item",
            status="404 NOT FOUND",
            viewopts=dict(item_name="DoesntExist"),
            params=dict(contenttype="text/plain"),
        )

    def test_modify_item(self):
        self._test_view("frontend.modify_item", status="200 OK", viewopts=dict(item_name="DoesntExist"))

    def test_rename_item(self):
        self._test_view("frontend.rename_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_delete_item(self):
        self._test_view("frontend.delete_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_index(self):
        self._test_view("frontend.index", status="200 OK", viewopts=dict(item_name="DoesntExist"))

    def test_forwardrefs(self):
        self._test_view("frontend.forwardrefs", status="200 OK", viewopts=dict(item_name="DoesntExist"))

    def test_backrefs(self):
        self._test_view("frontend.backrefs", status="200 OK", viewopts=dict(item_name="DoesntExist"))

    def test_history(self):
        self._test_view("frontend.history", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_diff(self):
        # TODO another test with valid rev1 and rev2 url args and an existing item is needed
        self._test_view("frontend.diff", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_similar_names(self):
        self._test_view("frontend.similar_names", viewopts=dict(item_name="DoesntExist"))

    def test_sitemap(self):
        self._test_view("frontend.sitemap", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_tagged_items(self):
        self._test_view("frontend.tagged_items", status="200 OK", viewopts=dict(tag="DoesntExist"))

    def test_root(self):
        self._test_view("frontend.index")

    def test_robots(self):
        self._test_view("frontend.robots", data=["Disallow:"], content_types=["text/plain; charset=utf-8"])

    def test_search(self):
        self._test_view("frontend.search")

    def test_revert_item(self):
        self._test_view(
            "frontend.revert_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist", rev="000000")
        )

    def test_mychanges(self):
        self._test_view("frontend.mychanges", viewopts=dict(userid="000000"))

    def test_global_history(self):
        self._test_view("frontend.global_history")

    def test_wanted_items(self):
        self._test_view("frontend.wanted_items")

    def test_orphaned_items(self):
        self._test_view("frontend.orphaned_items")

    def test_quicklink_item(self):
        self._test_view(
            "frontend.quicklink_item",
            status="302 FOUND",
            viewopts=dict(item_name="DoesntExist"),
            data=["<!doctype html"],
        )

    def test_subscribe_item(self):
        self._test_view("frontend.subscribe_item", status="404 NOT FOUND", viewopts=dict(item_name="DoesntExist"))

    def test_register(self):
        self._test_view("frontend.register")

    def test_verifyemail(self):
        self._test_view("frontend.verifyemail", status="302 FOUND", data=["<!doctype html"])

    def test_lostpass(self):
        self._test_view("frontend.lostpass")

    def test_recoverpass(self):
        self._test_view("frontend.recoverpass")

    def test_login(self):
        self._test_view("frontend.login")

    def test_logout(self):
        self._test_view("frontend.logout", status="302 FOUND", data=["<!doctype html"])

    def test_usersettings_notloggedin(self):
        # if a anon user visits usersettings view, he'll get redirected to the login view
        self._test_view("frontend.usersettings", status="302 FOUND", data=["<!doctype html"])

    # TODO: implement test_usersettings_loggedin()

    def test_bookmark(self):
        self._test_view("frontend.bookmark", status="302 FOUND", data=["<!doctype html"])

    def test_diffraw(self):
        # TODO another test with valid rev1 and rev2 url args and an existing item is needed
        self._test_view("frontend.diffraw", status="404 NOT FOUND", data=[], viewopts=dict(item_name="DoesntExist"))

    def test_global_tags(self):
        self._test_view("frontend.global_tags")


class TestUsersettings:
    reinit_storage = True  # avoid username / email collisions

    @pytest.fixture(autouse=True)
    def custom_setup(self, app):
        saved_user = flaskg.user
        flaskg.user = user.User()
        yield
        flaskg.user = saved_user

    def test_user_password_change(self):
        self.createUser("moin", "Xiwejr622")
        flaskg.user = user.User(name="moin", password="Xiwejr622")
        form = self.fillPasswordChangeForm("Xiwejr622", "Woodoo645", "Woodoo645")
        valid = form.validate()
        assert valid  # form data is valid

    def test_user_unicode_password_change(self):
        name = "moin"
        password = "__שם משתמש לא קיים__"  # Hebrew

        self.createUser(name, password)
        flaskg.user = user.User(name=name, password=password)
        form = self.fillPasswordChangeForm(password, "Woodoo645", "Woodoo645")
        valid = form.validate()
        assert valid  # form data is valid

    def test_user_password_change_to_unicode_pw(self):
        name = "moin"
        password = "Xiwejr622"
        new_password = "__שם משתמש לא קיים__"  # Hebrew

        self.createUser(name, password)
        flaskg.user = user.User(name=name, password=password)
        form = self.fillPasswordChangeForm(password, new_password, new_password)
        valid = form.validate()
        assert valid  # form data is valid

    def test_fail_user_password_change_pw_mismatch(self):
        self.createUser("moin", "Xiwejr622")
        flaskg.user = user.User(name="moin", password="Xiwejr622")
        form = self.fillPasswordChangeForm("Xiwejr622", "Piped33", "Woodoo645")
        valid = form.validate()
        # form data is invalid because password1 != password2
        assert not valid

    def test_fail_password_change(self):
        self.createUser("moin", "Xiwejr622")
        flaskg.user = user.User(name="moin", password="Xiwejr622")
        form = self.fillPasswordChangeForm("Xinetd33", "Woodoo645", "Woodoo645")
        valid = form.validate()
        # form data is invalid because password_current != user.password
        assert not valid

    # Helpers ---------------------------------------------------------

    def fillPasswordChangeForm(self, current_password, password1, password2):
        """helper to fill UserSettingsPasswordForm form"""
        FormClass = views.UserSettingsPasswordForm
        request_form = (
            ("password_current", current_password),
            ("password1", password1),
            ("password2", password2),
            ("submit", "Save"),
        )
        form = FormClass.from_flat(request_form)
        return form

    def createUser(self, name, password, pwencoded=False, email=None):
        """helper to create test user"""
        if email is None:
            email = "user@example.org"
        user.create_user(name, password, email, is_encrypted=pwencoded)
