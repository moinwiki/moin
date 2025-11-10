# Copyright: 2025 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from flask import url_for

from moin import user
from moin.constants.itemtypes import ITEMTYPE_DEFAULT
from moin.constants.keys import ITEMID

if TYPE_CHECKING:
    from flask.testing import FlaskClient
    from werkzeug.test import TestResponse


def set_user_in_client_session(client: FlaskClient, user: user.User) -> None:
    # the test configuration has MoinAuth enabled
    with client.session_transaction() as session:
        session["user.itemid"] = user.profile[ITEMID]
        session["user.trusted"] = False
        session["user.auth_method"] = "moin"
        session["user.auth_attribs"] = tuple()
        session["user.session_token"] = user.get_session_token()


def create_user(name: str, password: str, pwencoded: bool = False, email: str | None = None) -> None:
    """
    Helper to create test user
    """
    if email is None:
        email = "user@example.org"
    user.create_user(name, password, email, is_encrypted=pwencoded)


def login(client: FlaskClient, username: str, password: str, next: str = "http://localhost/Home") -> None:
    response = client.post(
        url_for("frontend.login"),
        follow_redirects=False,
        data={"login_username": username, "login_password": password, "login_nexturl": next, "login_submit": "1"},
    )
    assert response.status_code == 302
    assert response.location == next
    assert client.get_cookie("session")


def modify_item(
    client: FlaskClient, item_name: str, data: dict[str, Any], expected_status_code: int = 302
) -> TestResponse:
    response = client.post(url_for("frontend.modify_item", item_name=item_name), data=data)
    assert response.status_code == expected_status_code
    return response


def make_modify_form_data(
    item_name: str,
    *,
    content: str = "",
    comment: str = "",
    contenttype: str = "text/x.moin.wiki;charset=utf-8",
    **kwargs,
):
    return {
        "itemtype": ITEMTYPE_DEFAULT,
        "template": "",
        "contenttype": contenttype,
        "content_form_data_text": content,
        "content_form_data_file": content.encode(encoding="utf-8"),
        "comment": comment,
        "meta_form_acl": "None",
        "meta_form_name": item_name,
        "meta_form_summary": "",
        "meta_form_tags": "",
        "submit": "OK",
    } | kwargs
