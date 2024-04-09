# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007,2009 by MoinMoin:ThomasWaldmann
# Copyright: 2008 by MoinMoin:MelitaMihaljevic
# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# Copyright: 2010 by MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.backends.wiki_group tests
"""


import pytest

from flask import current_app as app
from flask import g as flaskg

from moin.datastructures.backends._tests import GroupsBackendTest
from moin.datastructures import GroupDoesNotExistError
from moin.constants.keys import NAME, USERGROUP
from moin.security import AccessControlList
from moin._tests import become_trusted, create_random_string_list, update_item


DATA = "This is a group item"


class TestWikiGroupBackend(GroupsBackendTest):

    # Suppose that default configuration for the groups is used which
    # is WikiGroups backend.

    @pytest.fixture(autouse=True)
    def custom_setup(self):
        become_trusted()
        for group, members in self.test_groups.items():
            update_item(group, {USERGROUP: members}, DATA)

    def test_rename_group_item(self):
        """
        Tests renaming of a group item.
        """
        become_trusted()
        update_item("SomeGroup", {USERGROUP: ["ExampleUser"]}, DATA)
        assert "ExampleUser" in flaskg.groups["SomeGroup"]
        pytest.raises(GroupDoesNotExistError, lambda: flaskg.groups["AnotherGroup"])

        update_item("SomeGroup", {NAME: ["AnotherGroup"], USERGROUP: ["ExampleUser"]}, DATA)
        assert "ExampleUser" in flaskg.groups["AnotherGroup"]
        pytest.raises(GroupDoesNotExistError, lambda: flaskg.groups["SomeGroup"])

    def test_appending_group_item(self):
        """
        Test scalability by appending a name to a large list of group members.
        """
        become_trusted()
        # long list of users
        members = create_random_string_list(length=15, count=1234)
        test_user = create_random_string_list(length=15, count=1)[0]
        update_item("UserGroup", {USERGROUP: members}, DATA)
        update_item("UserGroup", {USERGROUP: members + [test_user]}, "")
        result = test_user in flaskg.groups["UserGroup"]

        assert result

    def test_member_removed_from_group_item(self):
        """
        Tests appending a member to a large list of group members and
        recreating the item without the member.
        """
        become_trusted()

        # long list of users
        members = create_random_string_list()
        update_item("UserGroup", {USERGROUP: members}, DATA)

        # updates the text with the text_user
        test_user = create_random_string_list(length=15, count=1)[0]
        update_item("UserGroup", {USERGROUP: [test_user]}, DATA)
        result = test_user in flaskg.groups["UserGroup"]
        assert result

        # updates the text without test_user
        update_item("UserGroup", {}, DATA)
        result = test_user in flaskg.groups["UserGroup"]
        assert not result

    def test_wiki_backend_item_acl_usergroupmember_item(self):
        """
        Test if the wiki group backend works with acl code.
        First check acl rights of a user that is not a member of group
        then add user member to an item group and check acl rights
        """
        become_trusted()
        update_item("NewGroup", {USERGROUP: ["ExampleUser"]}, DATA)

        acl_rights = ["NewGroup:read,write"]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        has_rights_before = acl.may("AnotherUser", "read")

        # update item - add AnotherUser to a item group NewGroup
        update_item("NewGroup", {USERGROUP: ["AnotherUser"]}, "")

        has_rights_after = acl.may("AnotherUser", "read")

        assert (
            not has_rights_before
        ), "AnotherUser has no read rights because in the beginning he is not a member of a group item NewGroup"
        assert has_rights_after, "AnotherUser must have read rights because after appenditem he is member of NewGroup"


coverage_modules = ["moin.datastructures.backends.wiki_groups"]
