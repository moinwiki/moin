# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.backends.config_groups tests
"""


from moin.datastructures.backends._tests import GroupsBackendTest
from moin.datastructures import ConfigGroups
from moin._tests import wikiconfig

import pytest


class TestConfigGroupsBackend(GroupsBackendTest):
    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):

            def groups(self):
                groups = GroupsBackendTest.test_groups
                return ConfigGroups(groups)

        return Config


coverage_modules = ["moin.datastructures.backends.config_groups"]
