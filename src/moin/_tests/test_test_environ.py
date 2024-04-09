# Copyright: 2009 by MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Tests for our test environment
"""

from io import BytesIO

from flask import current_app as app
from flask import g as flaskg

from moin.constants.keys import NAME, CONTENTTYPE

from moin._tests import wikiconfig

import pytest


class TestStorageEnvironWithoutConfig:
    def setup_method(self, method):
        self.class_level_value = 123

    def test_fresh_backends(self):
        assert self.class_level_value == 123

        assert isinstance(app.cfg, wikiconfig.Config)

        storage = flaskg.storage
        assert storage
        assert hasattr(storage, "__getitem__")
        itemname = "this item shouldn't exist yet"
        assert not storage.has_item(itemname)
        item = storage[itemname]
        item.store_revision({NAME: [itemname], CONTENTTYPE: "text/plain;charset=utf-8"}, BytesIO(b""))
        assert storage.has_item(itemname)


DEFAULT_ACL = dict(
    before="+All:write",  # need to write to sys pages
    default="All:read,write,admin,create,destroy",
    after="Me:create",
    hierarchic=False,
)


class TestStorageEnvironWithConfig:

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            default_acl = DEFAULT_ACL

        return Config

    def test_config(self):
        assert isinstance(app.cfg, wikiconfig.Config)
        assert app.cfg.default_acl == DEFAULT_ACL
