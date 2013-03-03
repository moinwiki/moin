# Copyright: 2009 by MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Tests for our test environment
"""

from StringIO import StringIO

from flask import current_app as app
from flask import g as flaskg

from MoinMoin.constants.keys import NAME, CONTENTTYPE

from MoinMoin._tests import wikiconfig


class TestStorageEnvironWithoutConfig(object):
    def setup_method(self, method):
        self.class_level_value = 123

    def test_fresh_backends(self):
        assert self.class_level_value == 123

        assert isinstance(app.cfg, wikiconfig.Config)

        storage = flaskg.storage
        assert storage
        assert hasattr(storage, '__getitem__')
        itemname = u"this item shouldn't exist yet"
        assert not storage.has_item(itemname)
        item = storage[itemname]
        new_rev = item.store_revision({NAME: [itemname, ], CONTENTTYPE: u'text/plain;charset=utf-8'}, StringIO(''))
        assert storage.has_item(itemname)


CONTENT_ACL = dict(
    before="+All:write",  # need to write to sys pages
    default="All:read,write,admin,create,destroy",
    after="Me:create",
    hierarchic=False,
)


class TestStorageEnvironWithConfig(object):

    class Config(wikiconfig.Config):
        content_acl = CONTENT_ACL

    def test_config(self):
        assert isinstance(app.cfg, wikiconfig.Config)
        assert app.cfg.content_acl == CONTENT_ACL
