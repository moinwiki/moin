# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.datastructures.backends.config_groups tests.
"""

import pytest

from moin._tests import wikiconfig
from moin.datastructures import ConfigGroups
from moin.datastructures.backends._tests import GroupsBackendTest


class TestConfigGroupsBackend(GroupsBackendTest):
    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):

            def groups(self):
                groups = GroupsBackendTest.test_groups
                return ConfigGroups(groups)

        return Config


coverage_modules = ["moin.datastructures.backends.config_groups"]
