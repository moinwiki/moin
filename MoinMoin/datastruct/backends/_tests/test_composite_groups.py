
"""
MoinMoin.datastruct.backends.composite_groups test

@copyright: 2009 MoinMoin:DmitrijsMilajevs
@license: GPL, see COPYING for details
"""

from py.test import raises

from flask import flaskg

from MoinMoin.datastruct.backends._tests import GroupsBackendTest
from MoinMoin.datastruct import ConfigGroups, CompositeGroups, GroupDoesNotExistError
from MoinMoin._tests import wikiconfig
from MoinMoin import security


class TestCompositeGroupsBackend(GroupsBackendTest):

    class Config(wikiconfig.Config):

        def groups(self):
            groups = GroupsBackendTest.test_groups
            return CompositeGroups(ConfigGroups(groups))


class TestCompositeGroup(object):

    class Config(wikiconfig.Config):

        admin_group = frozenset([u'Admin', u'JohnDoe'])
        editor_group = frozenset([u'MainEditor', u'JohnDoe'])
        fruit_group = frozenset([u'Apple', u'Banana', u'Cherry'])

        first_backend_groups = {u'AdminGroup': admin_group,
                                u'EditorGroup': editor_group,
                                u'FruitGroup': fruit_group}

        user_group = frozenset([u'JohnDoe', u'Bob', u'Joe'])
        city_group = frozenset([u'Bolzano', u'Riga', u'London'])

        # Suppose, someone hacked second backend and added himself to AdminGroup
        second_admin_group = frozenset([u'TheHacker'])

        second_backend_groups = {u'UserGroup': user_group,
                                 u'CityGroup': city_group,
                                 # Here group name clash occurs.
                                 # AdminGroup is defined in both
                                 # first_backend and second_backend.
                                 u'AdminGroup': second_admin_group}

        def groups(self):
            return CompositeGroups(ConfigGroups(self.first_backend_groups),
                                   ConfigGroups(self.second_backend_groups))

    def setup_method(self, method):
        self.groups = flaskg.groups

    def test_getitem(self):
        raises(GroupDoesNotExistError, lambda: self.groups[u'NotExistingGroup'])

    def test_clashed_getitem(self):
        """
        Check the case when groups of the same name are defined in multiple
        backends. __getitem__ should return the first match (backends are
        considered in the order they are given in the backends list).
        """
        admin_group = self.groups[u'AdminGroup']

        # TheHacker added himself to the second backend, but that must not be
        # taken into consideration, because AdminGroup is defined in first
        # backend and we only use the first match.
        assert u'TheHacker' not in admin_group

    def test_iter(self):
        all_group_names = list(self.groups)

        assert 5 == len(all_group_names)
        # There are no duplicates
        assert len(set(all_group_names)) == len(all_group_names)

    def test_contains(self):
        assert u'UserGroup' in self.groups
        assert u'not existing group' not in self.groups


coverage_modules = ['MoinMoin.datastruct.backends.composite_groups']
