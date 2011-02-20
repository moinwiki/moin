# -*- coding: utf-8 -*-
"""
    MoinMoin - Tests for our test environment

    @copyright: 2009 by MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import py

from flask import current_app as app
from flask import flaskg

from MoinMoin.items import IS_SYSITEM, SYSITEM_VERSION
from MoinMoin.storage.error import NoSuchItemError

from MoinMoin._tests import wikiconfig

class TestStorageEnvironWithoutConfig(object):
    def setup_method(self, method):
        self.class_level_value = 123

    def test_fresh_backends(self):
        assert self.class_level_value == 123

        assert isinstance(app.cfg, wikiconfig.Config)

        storage = flaskg.storage
        assert storage
        assert hasattr(storage, 'get_item')
        assert hasattr(storage, 'history')
        assert not list(storage.iteritems())
        assert not list(storage.history())
        itemname = u"this item shouldn't exist yet"
        assert py.test.raises(NoSuchItemError, storage.get_item, itemname)
        item = storage.create_item(itemname)
        new_rev = item.create_revision(0)
        new_rev['name'] = itemname
        new_rev['mimetype'] = u'text/plain'
        item.commit()
        assert storage.has_item(itemname)
        assert not storage.has_item("FrontPage")

    # Run this test twice to see if something's changed
    test_twice = test_fresh_backends

class TestStorageEnvironWithConfig(object):
    class Config(wikiconfig.Config):
        load_xml = wikiconfig.Config._test_items_xml
        content_acl = dict(
            before="+All:write", # need to write to sys pages
            default="All:read,write,admin,create,destroy",
            after="Me:create",
            hierarchic=False,
        )

    def test_fresh_backends_with_content(self):
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
            new_rev['name'] = pagename
            new_rev['mimetype'] = u'text/plain'
            item.commit()

        itemname = u"OnlyForThisTest"
        assert not storage.has_item(itemname)
        new_item = storage.create_item(itemname)
        new_rev = new_item.create_revision(0)
        new_rev['name'] = itemname
        new_rev['mimetype'] = u'text/plain'
        new_item.commit()
        assert storage.has_item(itemname)

        assert storage.get_backend("/").after.acl_lines[0] == "Me:create"

    # Run this test twice to see if something's changed
    test_twice = test_fresh_backends_with_content

