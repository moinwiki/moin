# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.utils.notifications.
"""

from io import BytesIO

from flask import has_app_context, url_for

from moin import current_app, flaskg
from moin.constants.itemtypes import ITEMTYPE_DEFAULT
from moin.constants.keys import ACTION, ACTION_SAVE, ACTION_TRASH, ADDRESS, ITEMID, NAME, NAMESPACE, ITEMTYPE, PARENTID
from moin.items import Item
from moin.storage.middleware import indexing as msmi
from moin.utils.diff_datastruct import diff as dict_diff
from moin.utils import notifications
from moin.utils.notifications import Notification, DESTROY_REV, DESTROY_ALL, send_after_response, send_notifications
from moin.utils.names import split_fqname
from moin.utils.subscriptions import Subscriber

import pytest


@pytest.mark.usefixtures("_req_ctx", "custom_setup")
class TestNotifications:

    reinit_storage = True

    @pytest.fixture
    def custom_setup(self):
        self.imw = flaskg.unprotected_storage
        self.item_name = "foo"
        self.fqname = split_fqname(self.item_name)

    def store_revision(
        self, item: msmi.Item, data: bytes, *, parent: msmi.Revision | None = None, **kwargs
    ) -> msmi.Revision:
        meta = {ACTION: ACTION_SAVE, ADDRESS: "127.0.0.1", NAME: item.names.copy(), ITEMTYPE: ITEMTYPE_DEFAULT} | kwargs
        if parent:
            meta[PARENTID] = parent.revid
        revision = item.store_revision(meta, BytesIO(data), trusted=True, return_rev=True)
        assert revision
        return revision

    def test_get_content_diff(self):
        item = self.imw[self.item_name]
        rev1 = self.store_revision(item, b"x", contenttype="text/plain;charset=utf-8")
        notification = Notification(current_app, self.fqname, ACTION_SAVE, None, None, rev1.data, rev1.meta)
        assert notification.get_content_diff() == ["+ x"]
        rev1.data.seek(0, 0)

        rev2 = self.store_revision(item, b"xx", contenttype="text/plain;charset=utf-8")
        notification = Notification(current_app, self.fqname, ACTION_SAVE, rev1.data, rev1.meta, rev2.data, rev2.meta)
        assert notification.get_content_diff() == ["- x", "+ xx"]
        rev2.data.seek(0, 0)

        notification = Notification(current_app, self.fqname, ACTION_TRASH, rev2.data, rev2.meta, None, None)
        assert notification.get_content_diff() == ["- xx"]
        rev2.data.seek(0, 0)

        item = Item.create(self.item_name)
        notification = Notification(current_app, self.fqname, DESTROY_REV, rev2.data, rev2.meta, None, None)
        assert notification.get_content_diff() == ["- xx"]
        rev2.data.seek(0, 0)

        item = Item.create(self.item_name)
        notification = Notification(current_app, self.fqname, DESTROY_ALL, rev2.data, rev2.meta, None, None)
        assert notification.get_content_diff() == ["- xx"]

    def test_get_meta_diff(self):
        item = self.imw[self.item_name]
        rev1 = self.store_revision(item, b"x")
        notification = Notification(current_app, self.fqname, ACTION_SAVE, None, None, rev1.data, rev1.meta)
        assert notification.get_meta_diff() == dict_diff(dict(), rev1.meta._meta)

        rev2 = self.store_revision(item, b"xx")
        notification = Notification(current_app, self.fqname, ACTION_SAVE, rev1.data, rev1.meta, rev2.data, rev2.meta)
        assert notification.get_meta_diff() == dict_diff(rev1.meta._meta, rev2.meta._meta)

        actions = [DESTROY_REV, DESTROY_ALL, ACTION_TRASH]
        for action in actions:
            notification = Notification(current_app, self.fqname, action, rev2.data, rev2.meta, rev1.data, rev1.meta)
            assert notification.get_meta_diff() == dict_diff(rev2.meta._meta, dict())

    def test_generate_diff_url(self):
        domain = "http://test.com"
        notification = Notification(current_app, self.fqname, DESTROY_REV, None, None, None, None)
        assert notification.generate_diff_url(domain) == ""

        item = self.imw[self.item_name]
        rev1 = self.store_revision(item, b"x")
        notification = Notification(current_app, self.fqname, DESTROY_REV, rev1.data, rev1.meta, None, None)
        assert notification.generate_diff_url(domain) == ""

        rev2 = self.store_revision(item, b"xx")
        notification = Notification(current_app, self.fqname, DESTROY_REV, rev1.data, rev1.meta, rev2.data, rev2.meta)
        assert notification.generate_diff_url(domain) == "{}{}".format(
            domain, url_for("frontend.diff", item_name=self.item_name, rev1=rev1.revid, rev2=rev2.revid)
        )

    @pytest.mark.parametrize("mail_enabled", [False, True])
    def test_send_notifications_mail_disabled(self, monkeypatch, mail_enabled):
        # without mail, the subscribers are not even looked up
        lookups = []
        monkeypatch.setattr(current_app.cfg, "mail_enabled", mail_enabled)
        monkeypatch.setattr(notifications, "get_subscribers", lambda **meta: lookups.append(meta) or set())
        meta = {ITEMID: "0" * 32, NAME: [self.item_name], NAMESPACE: ""}
        send_notifications(current_app, self.fqname, ACTION_SAVE, new_data=BytesIO(b"x"), new_meta=meta)
        assert len(lookups) == int(mail_enabled)

    def test_send_notifications_bcc(self, monkeypatch):
        # subscribers must not see each other's addresses
        subscribers = {
            Subscriber("1" * 32, "one", "one@example.org", "en"),
            Subscriber("2" * 32, "two", "two@example.org", "en"),
            Subscriber("3" * 32, "three", "three@example.org", "de"),
        }
        mails = []
        monkeypatch.setattr(current_app.cfg, "mail_enabled", True)
        monkeypatch.setattr(notifications, "get_subscribers", lambda **meta: subscribers)
        monkeypatch.setattr(notifications, "send_after_response", mails.extend)
        meta = {ITEMID: "0" * 32, NAME: [self.item_name], NAMESPACE: ""}
        send_notifications(current_app, self.fqname, ACTION_SAVE, new_data=BytesIO(b"x"), new_meta=meta)
        assert sorted(sorted(mail["bcc"]) for mail in mails) == [
            ["one@example.org", "two@example.org"],
            ["three@example.org"],
        ]
        assert not any(mail.get("to") or mail.get("cc") for mail in mails)


MAILS = [
    dict(subject="first", text="text", to=["user@example.org"]),
    dict(subject="second", text="text", to=["other@example.org"]),
]


@pytest.fixture
def sent(monkeypatch):
    """Record the sendmail calls of moin.utils.notifications, the first one fails."""
    sent = []

    def sendmail(**mail):
        sent.append((mail["subject"], has_app_context()))
        if len(sent) == 1:
            raise OSError("mail server not reachable")

    monkeypatch.setattr(notifications, "sendmail", sendmail)
    return sent


def test_send_after_response(app, sent):
    with app.test_request_context("/"):
        send_after_response(MAILS)
        response = app.process_response(app.response_class("response body"))
    assert sent == []
    # the WSGI server closes the response after sending it
    response.close()
    # a failing mail does not keep the other mails from being sent
    assert sent == [("first", True), ("second", True)]


def test_send_without_request(_app_ctx, monkeypatch):
    sent = []
    monkeypatch.setattr(notifications, "sendmail", lambda **mail: sent.append(mail["subject"]))
    send_after_response(MAILS)
    assert sent == ["first", "second"]
