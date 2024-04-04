# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - config groups backend

The config_groups backend enables one to define groups and their
members in a configuration file.
"""


from moin.datastructures.backends import GreedyGroup, BaseGroupsBackend, GroupDoesNotExistError


class ConfigGroup(GreedyGroup):
    pass


class ConfigGroups(BaseGroupsBackend):

    def __init__(self, groups):
        """
        :param groups: Dictionary of groups where key is group name,
        and value is list of members of that group.
        """
        super().__init__()

        self._groups = groups

    def __contains__(self, group_name):
        return group_name in self._groups

    def __iter__(self):
        return iter(self._groups.keys())

    def __getitem__(self, group_name):
        return ConfigGroup(name=group_name, backend=self)

    def _retrieve_members(self, group_name):
        try:
            return self._groups[group_name]
        except KeyError:
            raise GroupDoesNotExistError(group_name)
