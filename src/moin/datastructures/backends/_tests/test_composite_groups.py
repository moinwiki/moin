# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
moin.datastructures.backends.composite_groups test
"""


from pytest import raises

from flask import g as flaskg

from moin.datastructures.backends._tests import GroupsBackendTest
from moin.datastructures import ConfigGroups, CompositeGroups, GroupDoesNotExistError
from moin._tests import wikiconfig

import pytest


class TestCompositeGroupsBackend(GroupsBackendTest):

    @pytest.fixture
    def cfg(self):

        class Config(wikiconfig.Config):

            def groups(self):
                groups = GroupsBackendTest.test_groups
                return CompositeGroups(ConfigGroups(groups))

        return Config


class TestCompositeGroup:

    @pytest.fixture
    def cfg(self):

        class Config(wikiconfig.Config):

            admin_group = frozenset(["Admin", "JohnDoe"])
            editor_group = frozenset(["MainEditor", "JohnDoe"])
            fruit_group = frozenset(["Apple", "Banana", "Cherry"])

            first_backend_groups = {"AdminGroup": admin_group, "EditorGroup": editor_group, "FruitGroup": fruit_group}

            user_group = frozenset(["JohnDoe", "Bob", "Joe"])
            city_group = frozenset(["Bolzano", "Riga", "London"])

            # Suppose, someone hacked second backend and added himself to AdminGroup
            second_admin_group = frozenset(["TheHacker"])

            second_backend_groups = {
                "UserGroup": user_group,
                "CityGroup": city_group,
                # Here group name clash occurs.
                # AdminGroup is defined in both
                # first_backend and second_backend.
                "AdminGroup": second_admin_group,
            }

            def groups(self):
                return CompositeGroups(
                    ConfigGroups(self.first_backend_groups), ConfigGroups(self.second_backend_groups)
                )

        return Config

    def test_getitem(self):
        raises(GroupDoesNotExistError, lambda: flaskg.groups["NotExistingGroup"])

    def test_clashed_getitem(self):
        """
        Check the case when groups of the same name are defined in multiple
        backends. __getitem__ should return the first match (backends are
        considered in the order they are given in the backends list).
        """
        admin_group = flaskg.groups["AdminGroup"]

        # TheHacker added himself to the second backend, but that must not be
        # taken into consideration, because AdminGroup is defined in first
        # backend and we only use the first match.
        assert "TheHacker" not in admin_group

    def test_iter(self):
        all_group_names = list(flaskg.groups)

        assert 5 == len(all_group_names)
        # There are no duplicates
        assert len(set(all_group_names)) == len(all_group_names)

    def test_contains(self):
        assert "UserGroup" in flaskg.groups
        assert "not existing group" not in flaskg.groups


coverage_modules = ["moin.datastructures.backends.composite_groups"]
