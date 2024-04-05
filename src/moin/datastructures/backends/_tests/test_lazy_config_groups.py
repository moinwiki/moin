# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.backends.config_lazy_groups tests
"""


from moin.datastructures.backends._tests import GroupsBackendTest
from moin.datastructures.backends.config_lazy_groups import ConfigLazyGroups
from moin.datastructures import ConfigGroups, CompositeGroups
from moin._tests import wikiconfig

import pytest


class TestLazyConfigGroups(GroupsBackendTest):

    test_groups = {
        "EditorGroup": ["John", "JoeDoe", "Editor1"],
        "AdminGroup": ["Admin1", "Admin2", "John"],
        "OtherGroup": ["SomethingOther"],
        "EmptyGroup": [],
    }

    expanded_groups = test_groups

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):

            def groups(self):
                groups = TestLazyConfigGroups.test_groups
                return ConfigLazyGroups(groups)

        return Config

    def test_contains_group(self):
        """
        ConfigLazyGroups can not contain other group members.

        This test does not make sense.
        """


class TestCompositeAndLazyConfigGroups(GroupsBackendTest):
    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):

            def groups(self):
                config_groups = {
                    "EditorGroup": ["AdminGroup", "John", "JoeDoe", "Editor1", "John"],
                    "RecursiveGroup": ["Something", "OtherRecursiveGroup"],
                    "OtherRecursiveGroup": ["RecursiveGroup", "Anything", "NotExistingGroup"],
                    "ThirdRecursiveGroup": ["ThirdRecursiveGroup", "Banana"],
                    "CheckNotExistingGroup": ["NotExistingGroup"],
                }

                lazy_groups = {
                    "AdminGroup": ["Admin1", "Admin2", "John"],
                    "OtherGroup": ["SomethingOther"],
                    "EmptyGroup": [],
                }

                return CompositeGroups(ConfigGroups(config_groups), ConfigLazyGroups(lazy_groups))

        return Config


coverage_modules = ["moin.datastructures.backends.config_lazy_groups"]
