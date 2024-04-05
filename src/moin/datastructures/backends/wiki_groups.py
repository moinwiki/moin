# Copyright: 2008 MoinMoin:ThomasWaldmann
# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# Copyright: 2010 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - wiki group backend

The wiki_groups backend allows to define groups on wiki items.

Normally, the name of the group item has to end with Group like
FriendsGroup. This lets MoinMoin recognize it as a group. This default
pattern could be changed (e.g. for non-english languages etc.), see
HelpOnConfiguration.
"""

from flask import g as flaskg

from moin.constants.keys import CURRENT, USERGROUP
from moin.datastructures.backends import GreedyGroup, BaseGroupsBackend, GroupDoesNotExistError


class WikiGroup(GreedyGroup):

    def _load_group(self):
        group_name = self.name
        if flaskg.unprotected_storage.has_item(group_name):
            members, member_groups = super()._load_group()
            return members, member_groups
        else:
            raise GroupDoesNotExistError(group_name)


class WikiGroups(BaseGroupsBackend):

    def __contains__(self, group_name):
        return self.is_group_name(group_name) and flaskg.unprotected_storage.has_item(group_name)

    def __iter__(self):
        """
        To find group pages, app.cfg.cache.item_group_regexact pattern is used.
        """
        # TODO: use whoosh to search for group_regex matching items
        item_list = [
            rev.fqname.value
            for rev in flaskg.unprotected_storage.documents()
            if self.item_group_regex.search(rev.fqname.value)
        ]
        return iter(item_list)

    def __getitem__(self, group_name):
        return WikiGroup(name=group_name, backend=self)

    def _retrieve_members(self, group_name):
        item = flaskg.unprotected_storage[group_name]
        rev = item[CURRENT]
        usergroup = rev.meta.get(USERGROUP, [])
        return usergroup
