# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.backends.config_groups tests
"""


from MoinMoin.datastruct.backends._tests import GroupsBackendTest
from MoinMoin.datastruct import ConfigGroups
from MoinMoin._tests import wikiconfig


class TestConfigGroupsBackend(GroupsBackendTest):

    class Config(wikiconfig.Config):

        def groups(self):
            groups = GroupsBackendTest.test_groups
            return ConfigGroups(groups)


coverage_modules = ['MoinMoin.datastruct.backends.config_groups']
