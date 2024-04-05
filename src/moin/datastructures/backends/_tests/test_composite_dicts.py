# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# Copyright: 2008 MoinMoin: MelitaMihaljevic
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
moin.datastructures.backends.composite_dicts test
"""


from moin.datastructures.backends._tests import DictsBackendTest
from moin.datastructures import ConfigDicts, CompositeDicts
from moin._tests import wikiconfig

import pytest


class TestCompositeDict(DictsBackendTest):

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):

            one_dict = {
                "SomeTestDict": {
                    "First": "first item",
                    "text with spaces": "second item",
                    "Empty string": "",
                    "Last": "last item",
                }
            }

            other_dict = {"SomeOtherTestDict": {"One": "1", "Two": "2"}}

            def dicts(self):
                return CompositeDicts(ConfigDicts(self.one_dict), ConfigDicts(self.other_dict))

        return Config


coverage_modules = ["moin.datastructures.backends.composite_dicts"]
