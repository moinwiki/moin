# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.utils.notifications Tests
"""

from io import BytesIO

from flask import g as flaskg
from flask import current_app as app
from flask import url_for

from moin.constants.keys import ACTION_SAVE, ACTION_TRASH
from moin.items import Item
from moin.utils.diff_datastruct import diff as dict_diff
from moin.utils.notifications import Notification, DESTROY_REV, DESTROY_ALL
from moin.utils.interwiki import split_fqname

import pytest


class TestNotifications:
    reinit_storage = True

    @pytest.fixture(autouse=True)
    def custom_setup(self):
        self.imw = flaskg.unprotected_storage
        self.item_name = "foo"
        self.fqname = split_fqname(self.item_name)

    def test_get_content_diff(self):
        item = self.imw[self.item_name]
        rev1 = item.store_revision(
            dict(name=[self.item_name], contenttype="text/plain;charset=utf-8"),
            BytesIO(b"x"),
            trusted=True,
            return_rev=True,
        )
        notification = Notification(app, self.fqname, ACTION_SAVE, None, None, rev1.data, rev1.meta)
        assert notification.get_content_diff() == ["+ x"]
        rev1.data.seek(0, 0)

        rev2 = item.store_revision(
            dict(name=[self.item_name], contenttype="text/plain;charset=utf-8"),
            BytesIO(b"xx"),
            trusted=True,
            return_rev=True,
        )
        notification = Notification(app, self.fqname, ACTION_SAVE, rev1.data, rev1.meta, rev2.data, rev2.meta)
        assert notification.get_content_diff() == ["- x", "+ xx"]
        rev2.data.seek(0, 0)

        notification = Notification(app, self.fqname, ACTION_TRASH, rev2.data, rev2.meta, None, None)
        assert notification.get_content_diff() == ["- xx"]
        rev2.data.seek(0, 0)

        item = Item.create(self.item_name)
        notification = Notification(app, self.fqname, DESTROY_REV, rev2.data, rev2.meta, None, None)
        assert notification.get_content_diff() == ["- xx"]
        rev2.data.seek(0, 0)

        item = Item.create(self.item_name)
        notification = Notification(app, self.fqname, DESTROY_ALL, rev2.data, rev2.meta, None, None)
        assert notification.get_content_diff() == ["- xx"]

    def test_get_meta_diff(self):
        item = self.imw[self.item_name]
        rev1 = item.store_revision(dict(name=[self.item_name]), BytesIO(b"x"), trusted=True, return_rev=True)
        notification = Notification(app, self.fqname, ACTION_SAVE, None, None, rev1.data, rev1.meta)
        assert notification.get_meta_diff() == dict_diff(dict(), rev1.meta._meta)

        rev2 = item.store_revision(dict(name=[self.item_name]), BytesIO(b"xx"), trusted=True, return_rev=True)
        notification = Notification(app, self.fqname, ACTION_SAVE, rev1.data, rev1.meta, rev2.data, rev2.meta)
        assert notification.get_meta_diff() == dict_diff(rev1.meta._meta, rev2.meta._meta)

        actions = [DESTROY_REV, DESTROY_ALL, ACTION_TRASH]
        for action in actions:
            notification = Notification(app, self.fqname, action, rev2.data, rev2.meta, rev1.data, rev1.meta)
            assert notification.get_meta_diff() == dict_diff(rev2.meta._meta, dict())

    def test_generate_diff_url(self):
        domain = "http://test.com"
        notification = Notification(app, self.fqname, DESTROY_REV, None, None, None, None)
        assert notification.generate_diff_url(domain) == ""

        item = self.imw[self.item_name]
        rev1 = item.store_revision(dict(name=[self.item_name]), BytesIO(b"x"), trusted=True, return_rev=True)
        notification = Notification(app, self.fqname, DESTROY_REV, rev1.data, rev1.meta, None, None)
        assert notification.generate_diff_url(domain) == ""

        rev2 = item.store_revision(dict(name=[self.item_name]), BytesIO(b"xx"), trusted=True, return_rev=True)
        notification = Notification(app, self.fqname, DESTROY_REV, rev1.data, rev1.meta, rev2.data, rev2.meta)
        assert notification.generate_diff_url(domain) == "{}{}".format(
            domain, url_for("frontend.diff", item_name=self.item_name, rev1=rev1.revid, rev2=rev2.revid)
        )
