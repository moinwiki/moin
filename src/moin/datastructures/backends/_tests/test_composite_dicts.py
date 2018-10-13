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

            one_dict = {u'SomeTestDict': {u'First': u'first item',
                                          u'text with spaces': u'second item',
                                          u'Empty string': u'',
                                          u'Last': u'last item'}}

            other_dict = {u'SomeOtherTestDict': {u'One': '1',
                                                 u'Two': '2'}}

            def dicts(self):
                return CompositeDicts(ConfigDicts(self.one_dict),
                                      ConfigDicts(self.other_dict))

        return Config


coverage_modules = ['moin.datastructures.backends.composite_dicts']
