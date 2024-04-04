# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - config group lazy backend.

    The config group backend allows one to define groups in a
    configuration file.

    NOTE that this is proof-of-concept implementation. LDAP backend
    should be based on this concept.
"""


from moin.datastructures.backends import LazyGroup, LazyGroupsBackend


class ConfigLazyGroup(LazyGroup):
    pass


class ConfigLazyGroups(LazyGroupsBackend):

    def __init__(self, groups):
        super().__init__()

        self._groups = groups

    def __contains__(self, group_name):
        return group_name in self._groups

    def __iter__(self):
        return iter(self._groups.keys())

    def __getitem__(self, group_name):
        return ConfigLazyGroup(group_name, self)

    def _iter_group_members(self, group_name):
        if group_name in self:
            return self._groups[group_name].__iter__()

    def _group_has_member(self, group_name, member):
        return group_name in self and member in self._groups[group_name]
