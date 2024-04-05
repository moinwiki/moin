# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007 by MoinMoin:ThomasWaldmann
# Copyright: 2008 by MoinMoin:MelitaMihaljevic
# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.datastructures.backends base test classes.
"""


from pytest import raises

from flask import current_app as app
from flask import g as flaskg

from moin.security import AccessControlList
from moin.datastructures import GroupDoesNotExistError


class GroupsBackendTest:

    test_groups = {
        "EditorGroup": ["AdminGroup", "John", "JoeDoe", "Editor1", "John"],
        "AdminGroup": ["Admin1", "Admin2", "John"],
        "OtherGroup": ["SomethingOther"],
        "RecursiveGroup": ["Something", "OtherRecursiveGroup"],
        "OtherRecursiveGroup": ["RecursiveGroup", "Anything", "NotExistingGroup"],
        "ThirdRecursiveGroup": ["ThirdRecursiveGroup", "Banana"],
        "EmptyGroup": [],
        "CheckNotExistingGroup": ["NotExistingGroup"],
    }

    expanded_groups = {
        "EditorGroup": ["Admin1", "Admin2", "John", "JoeDoe", "Editor1"],
        "AdminGroup": ["Admin1", "Admin2", "John"],
        "OtherGroup": ["SomethingOther"],
        "RecursiveGroup": ["Anything", "Something", "NotExistingGroup"],
        "OtherRecursiveGroup": ["Anything", "Something", "NotExistingGroup"],
        "ThirdRecursiveGroup": ["Banana"],
        "EmptyGroup": [],
        "CheckNotExistingGroup": ["NotExistingGroup"],
    }

    def test_contains(self):
        """
        Test group_wiki Backend and Group containment methods.
        """
        groups = flaskg.groups

        for group, members in self.expanded_groups.items():
            assert group in groups
            for member in members:
                assert member in groups[group]

        raises(GroupDoesNotExistError, lambda: groups["NotExistingGroup"])

    def test_contains_group(self):
        groups = flaskg.groups

        assert "AdminGroup" in groups["EditorGroup"]
        assert "EditorGroup" not in groups["AdminGroup"]

    def test_iter(self):
        groups = flaskg.groups

        for group, members in self.expanded_groups.items():
            returned_members = list(groups[group])
            assert len(returned_members) == len(members)
            for member in members:
                assert member in returned_members

    def test_get(self):
        groups = flaskg.groups

        assert groups.get("AdminGroup")
        assert "NotExistingGroup" not in groups
        assert groups.get("NotExistingGroup") is None
        assert groups.get("NotExistingGroup", []) == []

    def test_groups_with_member(self):
        groups = flaskg.groups

        john_groups = list(groups.groups_with_member("John"))
        assert 2 == len(john_groups)
        assert "EditorGroup" in john_groups
        assert "AdminGroup" in john_groups
        assert "ThirdGroup" not in john_groups

    def test_backend_acl_allow(self):
        """
        Test if the wiki group backend works with acl code.
        Check user which has rights.
        """
        acl_rights = ["AdminGroup:admin,read,write"]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        for user in self.expanded_groups["AdminGroup"]:
            for permission in ["read", "write", "admin"]:
                assert acl.may(
                    "Admin1", permission
                ), f"{user} must have {permission} permission because he is member of the AdminGroup"

    def test_backend_acl_deny(self):
        """
        Test if the wiki group backend works with acl code.
        Check user which does not have rights.
        """
        acl_rights = ["AdminGroup:read,write"]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        assert "SomeUser" not in flaskg.groups["AdminGroup"]
        for permission in ["read", "write"]:
            assert not acl.may(
                "SomeUser", permission
            ), f"SomeUser must not have {permission} permission because he is not listed in the AdminGroup"

        assert "Admin1" in flaskg.groups["AdminGroup"]
        assert not acl.may("Admin1", "admin")

    def test_backend_acl_with_all(self):
        acl_rights = ["EditorGroup:read,write,admin All:read"]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        for member in self.expanded_groups["EditorGroup"]:
            for permission in ["read", "write", "admin"]:
                assert acl.may(member, permission)

        assert acl.may("Someone", "read")
        for permission in ["write", "admin"]:
            assert not acl.may("Someone", permission)

    def test_backend_acl_not_existing_group(self):
        assert "NotExistingGroup" not in flaskg.groups

        acl_rights = ["NotExistingGroup:read,write,admin All:read"]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        assert not acl.may("Someone", "write")


class DictsBackendTest:

    dicts = {
        "SomeTestDict": {
            "First": "first item",
            "text with spaces": "second item",
            "Empty string": "",
            "Last": "last item",
        },
        "SomeOtherTestDict": {"One": "1", "Two": "2"},
    }

    def test_getitem(self):
        expected_dicts = self.dicts
        dicts = flaskg.dicts

        for dict_name, expected_dict in expected_dicts.items():
            test_dict = dicts[dict_name]
            assert len(test_dict) == len(expected_dict)
            for key, value in expected_dict.items():
                assert test_dict[key] == value

    def test_contains(self):
        dicts = flaskg.dicts

        for key in self.dicts:
            assert key in dicts

        assert "SomeNotExistingDict" not in dicts

    def test_update(self):
        dicts = flaskg.dicts

        d = {}
        d.update(dicts["SomeTestDict"])

        assert "First" in d

    def test_get(self):
        dicts = flaskg.dicts

        for dict_name in self.dicts:
            assert dicts.get(dict_name)

        assert "SomeNotExistingDict" not in dicts
        assert dicts.get("SomeNotExistingDict") is None
        assert dicts.get("SomeNotExistingDict", {}) == {}

        for dict_name, expected_dict in self.dicts.items():
            test_dict = dicts[dict_name]
            for key, value in expected_dict.items():
                assert "SomeNotExistingKey" not in test_dict
                assert test_dict.get("SomeNotExistingKey") is None
                assert test_dict.get("SomeNotExistingKey", {}) == {}
