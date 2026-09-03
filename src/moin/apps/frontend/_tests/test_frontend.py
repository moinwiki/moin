# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for frontend
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING, Iterable
from io import BytesIO

import json
import pytest

from flask import url_for
from werkzeug.datastructures import FileStorage

from moin import current_app, flaskg, themes, user
from moin.constants.keys import CURRENT, REVID
from moin.apps._tests.utils import (
    create_user,
    login,
    convert_item,
    modify_item,
    make_modify_form_data,
    set_user_in_client_session,
)
from moin.apps.frontend import views

if TYPE_CHECKING:
    from flask.testing import FlaskClient
    from werkzeug.test import TestResponse


def client_request(
    client: FlaskClient, method: str, url: str, *, user: user.User | None = None, **kwargs: Any
) -> TestResponse:
    if user is not None:
        set_user_in_client_session(client, user)
    print(f"client request: {method} {url}")
    return client.open(url, method=method, **kwargs)


@pytest.mark.usefixtures("_req_ctx")
class TestFrontend:

    def _test_view(
        self,
        viewname,
        *,
        status: str = "200 OK",
        data: Iterable[str] = ("<html>", "</html>"),
        content_types: Iterable[str] = ("text/html; charset=utf-8",),
        viewargs: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        user: user.User | None = None,
    ) -> TestResponse:

        if viewargs is None:
            viewargs = {}
        if params is None:
            params = {}

        with current_app.test_client() as client:

            request_url = url_for(viewname, **viewargs)

            response = client_request(client, "HEAD", request_url, user=user, data=params)
            assert response.status == status
            assert response.headers["Content-Type"] in content_types

            response = client_request(client, "GET", request_url, user=user, data=params)
            assert response.status == status
            assert response.headers["Content-Type"] in content_types
            rv_data = response.data.decode()
            for item in data:
                assert item in rv_data

            return response

    def _test_view_post(
        self,
        viewname: str,
        *,
        status: str = "302 FOUND",
        content_types: Iterable[str] = ("text/html; charset=utf-8",),
        data: Iterable[str] = ("<html>", "</html>"),
        form: dict[str, Any] | None = None,
        viewargs: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        user: user.User | None = None,
    ) -> TestResponse:

        if params is None:
            params = {}
        if viewargs is None:
            viewargs = {}
        if form is None:
            form = {}

        request_url = url_for(viewname, **viewargs)
        print("POST %s" % request_url)

        with current_app.test_client() as client:
            response = client_request(client, "POST", request_url, user=user, query_string=params, data=form)
            assert response.status == status
            assert response.headers["Content-Type"] in content_types
            rv_data = response.get_data(as_text=True)
            for item in data:
                assert item in rv_data
            return response

    def post_xhr_request(
        self,
        viewname: str,
        *,
        status: str = "302 FOUND",
        data: dict[str, Any] | None = None,
        viewargs: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        user: user.User | None = None,
        expected: dict[str, Any] = {},
    ) -> TestResponse:

        if params is None:
            params = {}
        if viewargs is None:
            viewargs = {}

        request_url = url_for(viewname, **viewargs)
        print("POST %s" % request_url)

        with current_app.test_client() as client:
            response = client_request(
                client,
                "POST",
                request_url,
                user=user,
                query_string=params,
                data=json.dumps(data),
                content_type="application/json; charset=utf-8",
            )
            assert response.status == status
            assert response.headers["Content-Type"] == "application/json"
            assert response.is_json
            rv_data = response.json
            assert isinstance(rv_data, dict)
            for key, val in expected.items():
                assert key in rv_data
                assert val == rv_data[key]
            return response

    def test_ajaxdelete_item_name_route(self):
        self.post_xhr_request(
            "frontend.ajaxdelete",
            status="200 OK",
            viewargs=dict(item_name="DoesntExist"),
            data=dict(itemnames='["DoesntExist"]', comment="Test"),
            expected={"itemnames": []},
        )

    def test_ajaxdelete_no_item_name_route(self):
        self.post_xhr_request(
            "frontend.ajaxdelete",
            status="200 OK",
            data=dict(itemnames='["DoesntExist"]', comment="Test"),
            expected={"itemnames": []},
        )

    def test_ajaxdestroy_item_name_route(self):
        self.post_xhr_request(
            "frontend.ajaxdestroy",
            status="200 OK",
            viewargs=dict(item_name="DoesntExist"),
            data=dict(itemnames='["DoesntExist"]', comment="Test"),
            expected={"itemnames": []},
        )

    def test_ajaxdestroy_no_item_name_route(self):
        self.post_xhr_request(
            "frontend.ajaxdestroy",
            status="200 OK",
            data=dict(comment="Test", itemnames='["DoesntExist"]'),
            expected={"itemnames": []},
        )

    def test_ajaxmodify(self):
        self._test_view_post("frontend.ajaxmodify", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

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
            viewargs=dict(item_name="WillBeCreated"),
        )

    def test_show_item(self):
        self._test_view("frontend.show_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_show_dom(self):
        self._test_view(
            "frontend.show_dom",
            status="404 NOT FOUND",
            data=["<?xml", ">"],
            viewargs=dict(item_name="DoesntExist"),
            content_types=["text/xml; charset=utf-8"],
        )

    def test_indexable(self):
        self._test_view("frontend.indexable", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_highlight_item(self):
        self._test_view("frontend.highlight_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_show_item_meta(self):
        self._test_view("frontend.show_item_meta", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_content_item(self):
        self._test_view("frontend.content_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_get_item(self):
        self._test_view("frontend.get_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_download_item(self):
        self._test_view("frontend.download_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_convert_item(self):
        self._test_view(
            "frontend.convert_item",
            status="404 NOT FOUND",
            viewargs=dict(item_name="DoesntExist"),
            params=dict(contenttype="text/plain"),
        )

    def test_modify_item(self):
        self._test_view("frontend.modify_item", status="200 OK", viewargs=dict(item_name="DoesntExist"))

    def test_modify_item_show_preview(self):

        create_user("björn", "Xiwejr622")
        test_user = flaskg.user = user.User(name="björn", password="Xiwejr622")

        content = "New item content."

        self._test_view_post(
            "frontend.modify_item",
            status="200 OK",
            viewargs=dict(item_name="quokka"),
            params={"itemtype": "default", "contenttype": "text/x.moin.wiki;charset=utf-8", "template": ""},
            form=make_modify_form_data("quokka", content=content, preview="Preview"),
            user=test_user,
        )

    def test_rename_item(self):
        self._test_view("frontend.rename_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_delete_item(self):
        self._test_view("frontend.delete_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_index(self):
        self._test_view("frontend.index", status="200 OK", viewargs=dict(item_name="DoesntExist"))

    def test_forwardrefs(self):
        self._test_view("frontend.forwardrefs", status="200 OK", viewargs=dict(item_name="DoesntExist"))

    def test_backrefs(self):
        self._test_view("frontend.backrefs", status="200 OK", viewargs=dict(item_name="DoesntExist"))

    def test_history(self):
        self._test_view("frontend.history", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_diff(self):
        # TODO: Add another test with valid rev1 and rev2 URL args and an existing item.
        self._test_view("frontend.diff", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_dispatch_missing_or_unknown_endpoint_returns_400(self):
        # A missing or unknown endpoint query param must return 400, not
        # raise KeyError/BuildError as an unhandled 500.
        with current_app.test_client() as client:
            assert client.get("/+dispatch").status_code == 400
            assert client.get("/+dispatch?endpoint=not-a-real-endpoint").status_code == 400
            # a valid endpoint still forwards
            rv = client.get("/+dispatch?endpoint=frontend.show_root")
            assert rv.status_code == 302

    def test_similar_names(self):
        self._test_view("frontend.similar_names", viewargs=dict(item_name="DoesntExist"))

    def test_sitemap(self):
        self._test_view("frontend.sitemap", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

    def test_tagged_items(self):
        self._test_view("frontend.tagged_items", status="200 OK", viewargs=dict(tag="DoesntExist"))

    def test_root(self):
        self._test_view("frontend.index")

    def test_robots(self):
        self._test_view("frontend.robots", data=["Disallow:"], content_types=["text/plain; charset=utf-8"])

    def test_search(self):
        self._test_view("frontend.search")

    def test_revert_item(self):
        self._test_view(
            "frontend.revert_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist", rev="000000")
        )

    def test_mychanges(self):
        self._test_view("frontend.mychanges", viewargs=dict(userid="000000"))

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
            viewargs=dict(item_name="DoesntExist"),
            data=["<!doctype html"],
        )

    def test_subscribe_item(self):
        self._test_view("frontend.subscribe_item", status="404 NOT FOUND", viewargs=dict(item_name="DoesntExist"))

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

    def test_login_post(self):
        username = "moin"
        password = "Xiwejr622"
        create_user(username, password)
        # same-origin target derived from the wiki's own URL, matching the
        # interwiki_map["Self"] base the test app is configured with
        nexturl = current_app.cfg.interwiki_map["Self"] + "Home"
        response = self._test_view_post(
            "frontend.login",
            form={
                "login_username": username,
                "login_password": password,
                "login_nexturl": nexturl,
                "login_submit": "1",
            },
            data=("Redirecting...",),
        )
        assert response.location == nexturl

    def test_login_post_open_redirect_blocked(self):
        # A crafted nexturl pointing off-site must not redirect the freshly
        # authenticated user away from the wiki; it falls back to the root.
        username = "moin"
        password = "Xiwejr622"
        create_user(username, password)
        response = self._test_view_post(
            "frontend.login",
            form={
                "login_username": username,
                "login_password": password,
                "login_nexturl": "https://evil.example/phish",
                "login_submit": "1",
            },
            data=("Redirecting...",),
        )
        # The fallback redirect is root-relative (e.g. "/"), never an
        # absolute URL, so an off-site host cannot appear in it.
        assert not response.location.startswith("http")
        assert "evil.example" not in response.location
        assert "/+" not in response.location

    def test_logout(self):
        self._test_view("frontend.logout", status="302 FOUND", data=["<!doctype html"])

    def test_usersettings_notloggedin(self):
        # If an anonymous user visits the usersettings view, they will be redirected to the login view.
        self._test_view("frontend.usersettings", status="302 FOUND", data=["<!doctype html"])

    # TODO: Implement test_usersettings_loggedin().

    def test_bookmark(self):
        self._test_view("frontend.bookmark", status="302 FOUND", data=["<!doctype html"])

    def test_diffraw(self):
        # TODO: Add another test with valid rev1 and rev2 URL args and an existing item.
        self._test_view("frontend.diffraw", status="404 NOT FOUND", data=[], viewargs=dict(item_name="DoesntExist"))

    def test_global_tags(self):
        self._test_view("frontend.global_tags")


class TestFrontendNew:

    def test_modify_item_show_preview(self, client):

        create_user("björn", "Xiwejr622")
        login(client, "björn", "Xiwejr622")
        modify_item(
            client,
            "quokka",
            make_modify_form_data("quokka", content="New item content.", preview="Preview"),
            expected_status_code=200,
        )

    def test_convert_item_to_markdown(self, client):
        create_user("björn", "Xiwejr622")
        login(client, "björn", "Xiwejr622")
        modify_item(client, "test1", make_modify_form_data("test1", content="moin test."))
        convert_item(
            client,
            "test1",
            # form data for for template "convert.html"
            {"new_type": "text/x-markdown;charset=utf-8", "comment": "test"},
        )


@pytest.fixture
def custom_setup():
    saved_user = flaskg.user
    flaskg.user = user.User()
    yield
    flaskg.user = saved_user


@pytest.mark.usefixtures("_req_ctx", "custom_setup")
class TestUsersettings:
    reinit_storage = True  # Avoid username/email collisions.

    def test_user_password_change(self):
        create_user("moin", "Xiwejr622")
        flaskg.user = user.User(name="moin", password="Xiwejr622")
        form = self.fillPasswordChangeForm("Xiwejr622", "Woodoo645", "Woodoo645")
        valid = form.validate()
        assert valid  # form data is valid

    def test_user_unicode_password_change(self):
        name = "moin"
        password = "__שם משתמש לא קיים__"  # Hebrew

        create_user(name, password)
        flaskg.user = user.User(name=name, password=password)
        form = self.fillPasswordChangeForm(password, "Woodoo645", "Woodoo645")
        valid = form.validate()
        assert valid  # form data is valid

    def test_user_password_change_to_unicode_pw(self):
        name = "moin"
        password = "Xiwejr622"
        new_password = "__שם משתמש לא קיים__"  # Hebrew

        create_user(name, password)
        flaskg.user = user.User(name=name, password=password)
        form = self.fillPasswordChangeForm(password, new_password, new_password)
        valid = form.validate()
        assert valid  # form data is valid

    def test_fail_user_password_change_pw_mismatch(self):
        create_user("moin", "Xiwejr622")
        flaskg.user = user.User(name="moin", password="Xiwejr622")
        form = self.fillPasswordChangeForm("Xiwejr622", "Piped33", "Woodoo645")
        valid = form.validate()
        # form data is invalid because password1 != password2
        assert not valid

    def test_fail_password_change(self):
        create_user("moin", "Xiwejr622")
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


def test_cspreport_get_does_not_crash(client):
    """
    Regression test: before_wiki()/teardown_wiki() skip environment setup
    for /+cspreport/log unconditionally, since only the dedicated
    cspreport() view is meant to handle that path. Previously that view
    was registered POST-only, so the path itself wasn't special to
    Werkzeug's routing -- a GET fell through to the generic show_item
    catch-all instead, which does need flaskg.storage, and crashed with
    AttributeError: storage since setup was skipped for it too.
    cspreport() is now registered for all methods and rejects non-POST
    itself with 405, so it -- not show_item -- is always the one handling
    this path, regardless of method.
    """
    rv = client.get(url_for("frontend.cspreport"))
    assert rv.status_code == 405

    # the real (POST) CSP report path must still work
    rv = client.post(
        url_for("frontend.cspreport"),
        data=json.dumps({"csp-report": {"document-uri": "http://localhost/"}}),
        content_type="application/csp-report",
    )
    assert rv.status_code == 204


def test_template_missing_file_returns_404(client):
    """
    Regression test: /+template/<filename> passed its filename straight
    to render_template() with no handling for a template that doesn't
    exist, crashing with an unhandled TemplateNotFound -- e.g. a browser
    speculatively probing for a nonexistent *.js.map next to a served
    .js file. Fixing that exposed a second bug: is_static_content() paths
    (which /+template/ is one of) skip the before_wiki() setup that
    injects cfg into the template context, so page_not_found()'s themed
    404.html crashed too (UndefinedError: 'cfg' is undefined) trying to
    render the error page itself.
    """
    rv = client.get(url_for("frontend.template", filename="does-not-exist.js.map"))
    assert rv.status_code == 404

    # a real template must still work
    rv = client.get(url_for("frontend.template", filename="dictionary.js"))
    assert rv.status_code == 200


def test_normal_item_404_is_still_themed(client):
    """
    page_not_found()'s plain-response fallback is scoped to
    is_static_content() paths only -- an ordinary missing item must still
    get the normal themed 404 page.
    """
    rv = client.get(url_for("frontend.show_item", item_name="DoesNotExist"))
    assert rv.status_code == 404
    assert b"moin-header" in rv.data


@pytest.mark.parametrize("theme_name", ["topside", "focus"])
@pytest.mark.parametrize(
    ("view_name", "special_view_title"),
    [
        ("frontend.global_history", "Global History"),
        ("frontend.index", "Global Index"),
        ("frontend.global_tags", "Global Tags"),
    ],
)
def test_special_view_title_is_not_appended_to_page_trail(
    client, monkeypatch, theme_name, view_name, special_view_title
):
    """Utility-view titles do not become an extra entry in the item trail."""
    theme = current_app.theme_manager.themes[theme_name]
    monkeypatch.setattr(themes, "get_current_theme", lambda: theme)
    with client.session_transaction() as session:
        session["trail"] = [("MoinTest/Home", [])]

    rv = client.get(url_for(view_name))
    assert rv.status_code == 200

    html = rv.get_data(as_text=True)
    marker = '<div class="moin-breadcrumb">' if theme_name == "focus" else '<ul class="moin-breadcrumb">'
    end_marker = "<!-- Breadcrumb - End -->" if theme_name == "focus" else "</ul>"
    start = html.index(marker)
    end = html.index(end_marker, start)
    breadcrumb = html[start:end]

    assert 'href="/Home"' in breadcrumb
    assert special_view_title not in breadcrumb


def test_show_old_revision_of_renamed_item(client):
    """
    Regression test: prior_next_revs() used to query the search index by the
    item's current name to build the revision list it then searches for the
    requested revid. A rename does not retroactively update older revisions'
    indexed NAME, so a name-based query only finds revisions from after the
    rename -- and viewing an older revision by its revid (e.g. from a link
    or bookmark made before the rename) raised an unhandled
    ValueError: '<revid>' is not in list.
    """
    create_user("moin", "Xiwejr622")
    login(client, "moin", "Xiwejr622")

    old_name = "OldRevNavName"
    new_name = "NewRevNavName"

    modify_item(client, old_name, make_modify_form_data(old_name, comment="first revision"))
    old_revid = flaskg.storage[old_name][CURRENT].meta[REVID]

    modify_item(client, old_name, make_modify_form_data(old_name, comment="before rename"))
    client.post(url_for("frontend.rename_item", item_name=old_name), data={"target": new_name, "comment": "renamed"})

    rv = client.get(url_for("frontend.show_item", item_name=new_name, rev=old_revid))
    assert rv.status_code == 200


def test_diff_includes_revisions_from_before_a_rename(client):
    """
    Regression test: diff() built its ALL_REVS query from fqname.query, i.e.
    the item's current name. A rename does not retroactively update older
    revisions' indexed NAME, so a name-based query -- the normal case, since
    that's what every link to this page uses -- only matched revisions from
    after the rename. rev_ids then never contained a pre-rename revid, so
    requesting a diff against one silently fell through to a different,
    unrequested revision instead of erroring or honoring the request.
    """
    create_user("moin", "Xiwejr622")
    login(client, "moin", "Xiwejr622")

    old_name = "OldDiffName"
    new_name = "NewDiffName"

    modify_item(client, old_name, make_modify_form_data(old_name, content="AAA\n", comment="first revision"))
    old_revid = flaskg.storage[old_name][CURRENT].meta[REVID]

    modify_item(client, old_name, make_modify_form_data(old_name, content="BBB\n", comment="before rename"))
    client.post(url_for("frontend.rename_item", item_name=old_name), data={"target": new_name, "comment": "renamed"})
    modify_item(client, new_name, make_modify_form_data(new_name, content="CCC\n", comment="after rename"))
    new_revid = flaskg.storage[new_name][CURRENT].meta[REVID]

    rv = client.get(url_for("frontend.diff", item_name=new_name, rev1=old_revid, rev2=new_revid))
    assert rv.status_code == 200
    # the pre-rename revision actually requested must be the one diffed
    # against, not a different one silently substituted for it
    assert b"AAA" in rv.data


def test_history_shows_revisions_from_before_a_rename(client):
    """
    Regression test: history() built its ALL_REVS query from fqname.query,
    i.e. the item's current name. A rename does not retroactively update
    older revisions' indexed NAME, so a name-based query -- the normal case,
    since that's what every link to this page uses -- only matched
    revisions from after the rename. The Item History page silently
    dropped everything before it instead of erroring, so nothing signalled
    the history was incomplete.
    """
    create_user("moin", "Xiwejr622")
    login(client, "moin", "Xiwejr622")

    old_name = "OldHistoryName"
    new_name = "NewHistoryName"

    modify_item(client, old_name, make_modify_form_data(old_name, comment="first revision"))
    modify_item(client, old_name, make_modify_form_data(old_name, comment="before rename"))
    client.post(url_for("frontend.rename_item", item_name=old_name), data={"target": new_name, "comment": "renamed"})
    modify_item(client, new_name, make_modify_form_data(new_name, comment="after rename"))

    rv = client.get(url_for("frontend.history", item_name=new_name))
    assert rv.status_code == 200
    assert b"first revision" in rv.data
    assert b"before rename" in rv.data
    assert b"after rename" in rv.data


def test_register_without_email_field_does_not_crash(client):
    """
    Regression test: RegistrationForm's email field had no Present()
    validator, so a POST that omits the email field entirely (e.g.
    scripted/bot traffic, not a real browser submission of the actual
    <form>) reached flatland's IsEmail validator with a None value and
    crashed with an unhandled AttributeError instead of just failing
    validation.
    """
    rv = client.post(
        url_for("frontend.register"),
        data={"register_username": "NoEmailUser", "register_password1": "Xiwejr622", "register_password2": "Xiwejr622"},
    )
    assert rv.status_code == 200


def test_register_with_malformed_email_is_rejected_not_crashed(client):
    """
    A present but invalid email must still be rejected normally -- only
    the missing/blank case was ever at risk of crashing.
    """
    rv = client.post(
        url_for("frontend.register"),
        data={
            "register_username": "BadEmailUser",
            "register_password1": "Xiwejr622",
            "register_password2": "Xiwejr622",
            "register_email": "not-an-email",
        },
    )
    assert rv.status_code == 200
    assert b"is not a valid email address" in rv.data


def test_register_with_valid_data_succeeds(client):
    """
    A normal, fully valid registration must still work.
    """
    rv = client.post(
        url_for("frontend.register"),
        data={
            "register_username": "GoodRegistrationUser",
            "register_password1": "Xiwejr622",
            "register_password2": "Xiwejr622",
            "register_email": "good-registration-user@example.org",
        },
    )
    assert rv.status_code == 302


def test_usersettings_ui_without_natural_fields_does_not_crash(client):
    """
    Regression test: Natural = AnyInteger.validated_by(ValueAtLeast(0))
    silently dropped AnyInteger's inherited Converted() validator, since
    .validated_by() replaces a validator list rather than appending to
    it. edit_rows and results_per_page (both Natural, neither optional)
    had no guard left to catch a missing value before ValueAtLeast(0),
    so a POST that omits them reached it with a None value and crashed
    with an unhandled TypeError instead of failing validation normally.
    """
    create_user("moin", "Xiwejr622")
    login(client, "moin", "Xiwejr622")

    rv = client.post(url_for("frontend.usersettings"), data={"part": "ui", "css_file": ""})
    assert rv.status_code == 200
    assert b"is not correct" in rv.data


def test_usersettings_ui_with_negative_value_is_rejected_not_crashed(client):
    """
    A present but invalid (negative) value must still be rejected
    normally -- only the missing/blank case was ever at risk of
    crashing.
    """
    create_user("moin", "Xiwejr622")
    login(client, "moin", "Xiwejr622")

    rv = client.post(
        url_for("frontend.usersettings"),
        data={"part": "ui", "css_file": "", "edit_rows": "-1", "results_per_page": "50"},
    )
    assert rv.status_code == 200
    assert b"must be greater than or equal to 0" in rv.data


def test_usersettings_ui_with_valid_data_succeeds(client):
    """
    A normal, fully valid settings update must still work.
    """
    create_user("moin", "Xiwejr622")
    login(client, "moin", "Xiwejr622")

    rv = client.post(
        url_for("frontend.usersettings"),
        data={"part": "ui", "css_file": "", "edit_rows": "10", "results_per_page": "25"},
    )
    assert rv.status_code == 200
    assert b'name="edit_rows" value="10"' in rv.data
    assert b'name="results_per_page" value="25"' in rv.data


def test_search_with_invalid_regex_does_not_crash(client, monkeypatch):
    """
    Regression test: search() used to catch re.PatternError for an invalid
    regex term, but PatternError only exists on Python 3.13+, so on 3.11/3.12
    the except clause itself raised AttributeError -- seen in production as
    "module 're' has no attribute 'PatternError'".
    """
    import re
    from whoosh.searching import Searcher

    def fake_search(self, *args, **kwargs):
        raise re.error("bad regex")

    monkeypatch.setattr(Searcher, "search", fake_search)

    rv = client.get(url_for("frontend.search"), query_string={"q": "test"})
    assert rv.status_code == 200
    assert b"invalid regex" in rv.data
