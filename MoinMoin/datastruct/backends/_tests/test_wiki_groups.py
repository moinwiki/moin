# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007,2009 by MoinMoin:ThomasWaldmann
# Copyright: 2008 by MoinMoin:MelitaMihaljevic
# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# Copyright: 2010 by MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.backends.wiki_group tests
"""


import pytest

from flask import current_app as app
from flask import g as flaskg

from MoinMoin.datastruct.backends._tests import GroupsBackendTest
from MoinMoin.datastruct import GroupDoesNotExistError
from MoinMoin.config import USERGROUP
from MoinMoin.security import AccessControlList
from MoinMoin.user import User
from MoinMoin._tests import become_trusted, create_random_string_list, update_item

DATA = "This is a group item"


class TestWikiGroupBackend(GroupsBackendTest):

    # Suppose that default configuration for the groups is used which
    # is WikiGroups backend.

    def setup_method(self, method):
        become_trusted()
        for group, members in self.test_groups.iteritems():
            update_item(group, 0, {USERGROUP: members}, DATA)

    def test_rename_group_item(self):
        """
        Tests renaming of a group item.
        """
        become_trusted()
        item = update_item(u'SomeGroup', 0, {USERGROUP: ["ExampleUser"]}, DATA)
        item.rename(u'AnotherGroup')

        result = u'ExampleUser' in flaskg.groups[u'AnotherGroup']
        assert result

        pytest.raises(GroupDoesNotExistError, lambda: flaskg.groups[u'SomeGroup'])

    def test_copy_group_item(self):
        """
        Tests copying a group item.
        """
        pytest.skip("item.copy() is not finished")

        become_trusted()
        item = update_item(u'SomeGroup', 0,  {USERGROUP: ["ExampleUser"]}, DATA)
        item.copy(u'SomeOtherGroup')

        result = u'ExampleUser' in flaskg.groups[u'SomeOtherGroup']
        assert result

        result = u'ExampleUser' in flaskg.groups[u'SomeGroup']
        assert result

    def test_appending_group_item(self):
        """
        Test scalability by appending a name to a large list of group members.
        """
        become_trusted()
        # long list of users
        members = create_random_string_list(length=15, count=1234)
        test_user = create_random_string_list(length=15, count=1)[0]
        update_item(u'UserGroup', 0, {USERGROUP: members}, DATA)
        update_item(u'UserGroup', 1, {USERGROUP: members + [test_user]}, '')
        result = test_user in flaskg.groups['UserGroup']

        assert result

    def test_member_removed_from_group_item(self):
        """
        Tests appending a member to a large list of group members and
        recreating the item without the member.
        """
        become_trusted()

        # long list of users
        members = create_random_string_list()
        update_item(u'UserGroup', 0,  {USERGROUP: members}, DATA)

        # updates the text with the text_user
        test_user = create_random_string_list(length=15, count=1)[0]
        update_item(u'UserGroup', 1,  {USERGROUP: [test_user]}, DATA)
        result = test_user in flaskg.groups[u'UserGroup']
        assert result

        # updates the text without test_user
        update_item(u'UserGroup', 2, {}, DATA)
        result = test_user in flaskg.groups[u'UserGroup']
        assert not result

    def test_wiki_backend_item_acl_usergroupmember_item(self):
        """
        Test if the wiki group backend works with acl code.
        First check acl rights of a user that is not a member of group
        then add user member to an item group and check acl rights
        """
        become_trusted()
        update_item(u'NewGroup', 0, {USERGROUP: ["ExampleUser"]}, DATA)

        acl_rights = ["NewGroup:read,write"]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        has_rights_before = acl.may(u"AnotherUser", "read")

        # update item - add AnotherUser to a item group NewGroup
        update_item(u'NewGroup', 1, {USERGROUP: ["AnotherUser"]}, '')

        has_rights_after = acl.may(u"AnotherUser", "read")

        assert not has_rights_before, 'AnotherUser has no read rights because in the beginning he is not a member of a group item NewGroup'
        assert has_rights_after, 'AnotherUser must have read rights because after appenditem he is member of NewGroup'

coverage_modules = ['MoinMoin.datastruct.backends.wiki_groups']

