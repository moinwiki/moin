# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.backends.config_dicts tests
"""


from  MoinMoin.datastruct.backends._tests import DictsBackendTest
from MoinMoin.datastruct import ConfigDicts
from MoinMoin._tests import wikiconfig


class TestConfigDictsBackend(DictsBackendTest):

    class Config(wikiconfig.Config):

        def dicts(self):
            dicts = DictsBackendTest.dicts
            return ConfigDicts(dicts)


coverage_modules = ['MoinMoin.datastruct.backends.config_dicts']

