# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.notifications Tests
"""

from io import StringIO

from flask import g as flaskg
from flask import current_app as app
from flask import url_for

from MoinMoin.constants.keys import ACTION_SAVE, ACTION_TRASH
from MoinMoin.items import Item
from MoinMoin.util.diff_datastruct import diff as dict_diff
from MoinMoin.util.notifications import Notification, get_item_last_revisions, DESTROY_REV, DESTROY_ALL
from MoinMoin.util.interwiki import split_fqname

import pytest


class TestNotifications(object):
    reinit_storage = True

    @pytest.fixture(autouse=True)
    def custom_setup(self):
        self.imw = flaskg.unprotected_storage
        self.item_name = u"foo"
        self.fqname = split_fqname(self.item_name)

    def test_get_last_item_revisions(self):
        assert get_item_last_revisions(app, self.fqname) == []
        item = self.imw[self.item_name]
        rev1 = item.store_revision(dict(name=[self.item_name, ]),
                                   StringIO(u'x'), trusted=True, return_rev=True)
        assert get_item_last_revisions(app, self.fqname) == [rev1]
        rev2 = item.store_revision(dict(name=[self.item_name, ]),
                                   StringIO(u'xx'), trusted=True, return_rev=True)
        assert get_item_last_revisions(app, self.fqname) == [rev2, rev1]
        rev3 = item.store_revision(dict(name=[self.item_name, ]),
                                   StringIO(u'xxx'), trusted=True, return_rev=True)
        assert get_item_last_revisions(app, self.fqname) == [rev3, rev2]

    def test_get_content_diff(self):
        item = self.imw[self.item_name]
        rev1 = item.store_revision(dict(name=[self.item_name, ], contenttype='text/plain'),
                                   StringIO(u'x'), trusted=True, return_rev=True)
        notification = Notification(app, self.fqname, [rev1], action=ACTION_SAVE)
        assert notification.get_content_diff() == ["+ x"]
        rev1.data.seek(0, 0)

        rev2 = item.store_revision(dict(name=[self.item_name, ], contenttype='text/plain'),
                                   StringIO(u'xx'), trusted=True, return_rev=True)
        notification = Notification(app, self.fqname, [rev2, rev1], action=ACTION_SAVE)
        assert notification.get_content_diff() == ['- x', '+ xx']
        rev2.data.seek(0, 0)

        notification = Notification(app, self.fqname, [rev2, rev1], action=ACTION_TRASH)
        assert notification.get_content_diff() == ['- xx']
        rev2.data.seek(0, 0)

        item = Item.create(self.item_name)
        notification = Notification(app, self.fqname, [], content=item.rev.data,
                                    meta=rev2.meta, action=DESTROY_REV)
        assert notification.get_content_diff() == ['- xx']
        rev2.data.seek(0, 0)

        item = Item.create(self.item_name)
        notification = Notification(app, self.fqname, [], content=item.rev.data,
                                    meta=rev2.meta, action=DESTROY_ALL)
        assert notification.get_content_diff() == ['- xx']

    def test_get_meta_diff(self):
        item = self.imw[self.item_name]
        rev1 = item.store_revision(dict(name=[self.item_name, ]), StringIO(u'x'),
                                   trusted=True, return_rev=True)
        notification = Notification(app, self.fqname, [rev1], action=ACTION_SAVE)
        assert notification.get_meta_diff() == dict_diff(dict(), rev1.meta._meta)

        rev2 = item.store_revision(dict(name=[self.item_name, ]), StringIO(u'xx'),
                                   trusted=True, return_rev=True)
        notification = Notification(app, self.fqname, [rev2, rev1], action=ACTION_SAVE)
        assert notification.get_meta_diff() == dict_diff(rev1.meta._meta, rev2.meta._meta)

        actions = [DESTROY_REV, DESTROY_ALL, ACTION_TRASH, ]
        for action in actions:
            notification = Notification(app, self.fqname, [rev2, rev1], meta=rev2.meta, action=action)
            assert notification.get_meta_diff() == dict_diff(rev2.meta._meta, dict())

    def test_generate_diff_url(self):
        domain = "http://test.com"
        notification = Notification(app, self.fqname, [], action=DESTROY_REV)
        assert notification.generate_diff_url(domain) == u""

        item = self.imw[self.item_name]
        rev1 = item.store_revision(dict(name=[self.item_name, ]), StringIO(u'x'),
                                   trusted=True, return_rev=True)
        notification.revs = [rev1]
        assert notification.generate_diff_url(domain) == u""

        rev2 = item.store_revision(dict(name=[self.item_name, ]), StringIO(u'xx'),
                                   trusted=True, return_rev=True)
        notification.revs = [rev2, rev1]
        assert notification.generate_diff_url(domain) == u"{0}{1}".format(
            domain, url_for('frontend.diff', item_name=self.item_name,
                            rev1=rev1.revid, rev2=rev2.revid))
