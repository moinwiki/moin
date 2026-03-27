# Copyright: 2009 by MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for our test environment.
"""

from io import BytesIO

from moin import current_app, flaskg
from moin.constants.itemtypes import ITEMTYPE_DEFAULT
from moin.constants.keys import ITEMTYPE, NAME, CONTENTTYPE

from moin._tests import wikiconfig

import pytest


@pytest.mark.usefixtures("_req_ctx")
class TestStorageEnvironWithoutConfig:

    def setup_method(self, method):
        self.class_level_value = 123

    def test_fresh_backends(self):
        assert self.class_level_value == 123

        assert isinstance(current_app.cfg, wikiconfig.Config)

        storage = flaskg.storage
        assert storage
        assert hasattr(storage, "__getitem__")
        itemname = "this item shouldn't exist yet"
        assert not storage.has_item(itemname)
        item = storage[itemname]
        item.store_revision(
            {NAME: [itemname], CONTENTTYPE: "text/plain;charset=utf-8", ITEMTYPE: ITEMTYPE_DEFAULT}, BytesIO(b"")
        )
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

    @pytest.mark.usefixtures("_app_ctx")
    def test_config(self):
        assert isinstance(current_app.cfg, wikiconfig.Config)
        assert current_app.cfg.default_acl == DEFAULT_ACL
