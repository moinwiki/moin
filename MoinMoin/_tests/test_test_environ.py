# Copyright: 2009 by MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Tests for our test environment
"""


import pytest

from flask import current_app as app
from flask import g as flaskg

from MoinMoin.conftest import init_test_app, deinit_test_app
from MoinMoin.config import NAME, CONTENTTYPE, IS_SYSITEM, SYSITEM_VERSION
from MoinMoin.storage.error import NoSuchItemError
from MoinMoin.storage.middleware.serialization import serialize, unserialize

from MoinMoin._tests import wikiconfig

class TestStorageEnvironWithoutConfig(object):
    def setup_method(self, method):
        self.class_level_value = 123
        app, ctx = init_test_app(wikiconfig.Config)

    def test_fresh_backends(self):
        assert self.class_level_value == 123

        assert isinstance(app.cfg, wikiconfig.Config)

        storage = flaskg.storage
        assert storage
        assert hasattr(storage, 'get_item')
        assert not list(storage.iteritems())
        itemname = u"this item shouldn't exist yet"
        assert pytest.raises(NoSuchItemError, storage.get_item, itemname)
        item = storage.create_item(itemname)
        new_rev = item.create_revision(0)
        new_rev[NAME] = itemname
        new_rev[CONTENTTYPE] = u'text/plain'
        item.commit()
        assert storage.has_item(itemname)
        assert not storage.has_item("FrontPage")

    # Run this test twice to see if something's changed
    test_twice = test_fresh_backends


class TestStorageEnvironWithConfig(object):
    class Config(wikiconfig.Config):
        content_acl = dict(
            before="+All:write", # need to write to sys pages
            default="All:read,write,admin,create,destroy",
            after="Me:create",
            hierarchic=False,
        )

    def test_fresh_backends_with_content(self):
        # get the items from xml file
        backend = app.unprotected_storage
        unserialize(backend, self.Config._test_items_xml)

        assert isinstance(app.cfg, wikiconfig.Config)

        storage = flaskg.storage
        should_be_there = (u"FrontPage", u"HelpOnLinking", u"HelpOnMoinWikiSyntax", )
        for pagename in should_be_there:
            assert storage.has_item(pagename)
            item = storage.get_item(pagename)
            rev = item.get_revision(-1)
            assert rev.revno == 0
            assert rev[IS_SYSITEM]
            assert rev[SYSITEM_VERSION] == 1
            # check whether this dirties the backend for the second iteration of the test
            new_rev = item.create_revision(1)
            new_rev[NAME] = pagename
            new_rev[CONTENTTYPE] = u'text/plain'
            item.commit()

        itemname = u"OnlyForThisTest"
        assert not storage.has_item(itemname)
        new_item = storage.create_item(itemname)
        new_rev = new_item.create_revision(0)
        new_rev[NAME] = itemname
        new_rev[CONTENTTYPE] = u'text/plain'
        new_item.commit()
        assert storage.has_item(itemname)

        assert storage.get_backend("/").after.acl_lines[0] == "Me:create"

    # Run this test twice to see if something's changed
    test_twice = test_fresh_backends_with_content

