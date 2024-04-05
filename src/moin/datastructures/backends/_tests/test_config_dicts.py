# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.backends.config_dicts tests
"""


from moin.datastructures.backends._tests import DictsBackendTest
from moin.datastructures import ConfigDicts
from moin._tests import wikiconfig

import pytest


class TestConfigDictsBackend(DictsBackendTest):

    @pytest.fixture
    def cfg(self):

        class Config(wikiconfig.Config):

            def dicts(self):
                dicts = DictsBackendTest.dicts
                return ConfigDicts(dicts)

        return Config

    def test__iter__(self):
        ConfigDicts_obj = ConfigDicts(DictsBackendTest.dicts)
        test_keyiterator = ConfigDicts.__iter__(ConfigDicts_obj)
        expected = ["SomeTestDict", "SomeOtherTestDict"]
        for result in test_keyiterator:
            assert result in expected


coverage_modules = ["moin.datastructures.backends.config_dicts"]
