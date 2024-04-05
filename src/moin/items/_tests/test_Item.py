# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.items Tests
"""

import pytest

from moin._tests import become_trusted, update_item
from moin.items import Item, NonExistent, IndexEntry, MixedIndexEntry
from moin.utils.interwiki import CompositeName
from moin.constants.keys import (
    ITEMTYPE,
    CONTENTTYPE,
    NAME,
    NAME_OLD,
    COMMENT,
    ADDRESS,
    TRASH,
    ITEMID,
    NAME_EXACT,
    SIZE,
    MTIME,
    REV_NUMBER,
    NAMESPACE,
    ACTION,
    ACTION_REVERT,
)
from moin.constants.namespaces import NAMESPACE_DEFAULT
from moin.constants.contenttypes import CONTENTTYPE_NONEXISTENT
from moin.constants.itemtypes import ITEMTYPE_NONEXISTENT


def build_dirs_index(basename, relnames):
    """
    Build a list of IndexEntry by hand, useful as a test helper for index testing.
    Dirs are files with subitems and have meta == {}.
    """
    return [
        (IndexEntry(relname, CompositeName(NAMESPACE_DEFAULT, NAME_EXACT, "/".join((basename, relname))), {}))
        for relname in relnames
    ]


def build_index(basename, relnames):
    """
    Build a list of IndexEntry by hand, useful as a test helper for index testing.
    Files have no subitems, meta content is reduced to required keys.
    """
    files = [
        (
            IndexEntry(
                relname,
                CompositeName(NAMESPACE_DEFAULT, NAME_EXACT, "/".join((basename, relname))),
                Item.create("/".join((basename, relname))).meta,
            )
        )
        for relname in relnames
    ]
    return [
        (
            IndexEntry(
                f.relname,
                f.fullname,
                {key: f.meta[key] for key in (CONTENTTYPE, ITEMTYPE, SIZE, MTIME, REV_NUMBER, NAMESPACE, ADDRESS)},
            )
        )
        for f in files
    ]


def build_mixed_index(basename, spec):
    """
    Build a list of MixedIndexEntry by hand, useful as a test helper for index testing.
    The mixed index is a combo of dirs and files with empty meta (dirs) or reduced
    meta (files).

    :spec is a list of (relname, hassubitem) tuples.
    """
    files = [
        (
            MixedIndexEntry(
                relname,
                CompositeName(NAMESPACE_DEFAULT, NAME_EXACT, "/".join((basename, relname))),
                Item.create("/".join((basename, relname))).meta,
                hassubitem,
            )
        )
        for relname, hassubitem in spec
    ]
    return [
        (
            MixedIndexEntry(
                f.relname,
                f.fullname,
                {} if f.hassubitems else {key: f.meta[key] for key in (CONTENTTYPE, ITEMTYPE)},
                f.hassubitems,
            )
        )
        for f in files
    ]


def fix_meta(files, builds):
    """
    Fix potential problem of datetimes being slightly different within files and builds metadata.
    Also fix problem where userid is in files metadata but missing from builds metadata.
    """
    fix_files = []
    fix_builds = []
    for idx in range(len(files)):
        fix_file = files[idx]
        fix_file.meta.pop("mtime", None)
        fix_file.meta.pop("userid", None)
        fix_files.append(fix_file)
    for idx in range(len(builds)):
        fix_build = builds[idx]
        fix_build.meta.pop("mtime", None)
        fix_build.meta.pop("userid", None)
        fix_builds.append(fix_build)
    return fix_files, fix_builds


class TestItem:

    def testNonExistent(self):
        item = Item.create("DoesNotExist")
        assert isinstance(item, NonExistent)
        meta, data = item.meta, item.content.data
        assert meta == {
            ITEMTYPE: ITEMTYPE_NONEXISTENT,
            CONTENTTYPE: CONTENTTYPE_NONEXISTENT,
            NAME: ["DoesNotExist"],
            NAMESPACE: "",
        }
        assert data == ""

    def testCRUD(self):
        name = "NewItem"
        contenttype = "text/plain;charset=utf-8"
        data = b"foobar"
        meta = {"foo": "bar", CONTENTTYPE: contenttype}
        comment = "saved it"
        become_trusted()
        item = Item.create(name)
        # save rev 0
        item._save(meta, data, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = item.meta, item.content.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data

        data *= 10000
        comment += " again"
        # save rev 1
        item._save(meta, data, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.content.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data

        data = ""
        comment = "saved empty data"
        # save rev 2 (auto delete)
        item._save(meta, data, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.content.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == b""

    def testIndex(self):
        # create a toplevel and some sub-items
        basename = "Foo"
        for name in ["", "/ab", "/cd/ef", "/gh", "/ij", "/ij/kl"]:
            item = Item.create(basename + name)
            item._save({CONTENTTYPE: "text/plain;charset=utf-8", ITEMTYPE: "default"}, "foo")
        item = Item.create(basename + "/mn")
        item._save({CONTENTTYPE: "image/jpeg", ITEMTYPE: "default"}, b"JPG")

        baseitem = Item.create(basename)

        # test Item.make_flat_index
        # TODO: test Item.get_subitem_revs
        dirs, files = baseitem.get_index()
        assert dirs == build_dirs_index(basename, ["cd", "ij"])

        # after +index converted to table output it shows subitems
        builds = build_index(basename, ["ab", "cd/ef", "gh", "ij", "ij/kl", "mn"])
        # fix potential problem of datetime and userid being different
        fix_files, fix_builds = fix_meta(files, builds)
        assert fix_files == fix_builds

        # check filtered index when startswith param is passed
        dirs, files = baseitem.get_index(startswith="a")
        assert dirs == []
        builds = build_index(basename, ["ab"])
        fix_files, fix_builds = fix_meta(files, builds)
        assert fix_files == fix_builds

        # check filtered index when contenttype_groups is passed
        ctgroups = ["Other Text Items"]
        dirs, files = baseitem.get_index(selected_groups=ctgroups)
        assert dirs == build_dirs_index(basename, ["cd", "ij"])
        # mn missing from results because it is image/jpeg, cd was never created
        builds = build_index(basename, ["ab", "cd/ef", "gh", "ij", "ij/kl"])
        fix_files, fix_builds = fix_meta(files, builds)
        assert fix_files == fix_builds

    def test_meta_filter(self):
        name = "Test_item"
        contenttype = "text/plain;charset=utf-8"
        meta = {"test_key": "test_val", CONTENTTYPE: contenttype, NAME: ["test_name"], ADDRESS: "1.2.3.4"}
        item = Item.create(name)
        result = Item.meta_filter(item, meta)
        # keys like NAME, ITEMID, REVID, DATAID are filtered
        expected = {"test_key": "test_val", CONTENTTYPE: contenttype}
        assert result == expected

    def test_meta_dict_to_text(self):
        name = "Test_item"
        contenttype = "text/plain;charset=utf-8"
        meta = {"test_key": "test_val", CONTENTTYPE: contenttype, NAME: ["test_name"]}
        item = Item.create(name)
        result = Item.meta_dict_to_text(item, meta)
        expected = '{\n  "contenttype": "text/plain;charset=utf-8",\n  "test_key": "test_val"\n}'
        assert result == expected

    def test_meta_text_to_dict(self):
        name = "Test_item"
        contenttype = "text/plain;charset=utf-8"
        text = (
            '{\n  "contenttype": "text/plain;charset=utf-8", \n  "test_key": "test_val", \n "name": ["test_name"] \n}'
        )
        item = Item.create(name)
        result = Item.meta_text_to_dict(item, text)
        expected = {"test_key": "test_val", CONTENTTYPE: contenttype}
        assert result == expected

    def test_item_can_have_several_names(self):
        content = b"This is page content"

        update_item("Page", {NAME: ["Page", "Another name"], CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, content)

        item1 = Item.create("Page")
        assert item1.name == "Page"
        assert item1.meta[CONTENTTYPE] == "text/x.moin.wiki;charset=utf-8"
        assert item1.content.data == content

        item2 = Item.create("Another name")
        assert item2.name == "Another name"
        assert item2.meta[CONTENTTYPE] == "text/x.moin.wiki;charset=utf-8"
        assert item2.content.data == content
        assert item1.rev.revid == item2.rev.revid

    def test_rename(self):
        name = "Test_Item"
        contenttype = "text/plain;charset=utf-8"
        data = "test_data"
        meta = {"test_key": "test_value", CONTENTTYPE: contenttype}
        comment = "saved it"
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        # item and its contents before renaming
        item = Item.create(name)
        assert item.name == "Test_Item"
        assert item.meta[COMMENT] == "saved it"
        new_name = "Test_new_Item"
        item.rename(new_name, comment="renamed")
        # item at original name and its contents after renaming
        item = Item.create(name)
        assert item.name == "Test_Item"
        # this should be a fresh, new item, NOT the stuff we renamed:
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT
        # item at new name and its contents after renaming
        item = Item.create(new_name)
        assert item.name == "Test_new_Item"
        assert item.meta[NAME_OLD] == ["Test_Item"]
        assert item.meta[COMMENT] == "renamed"
        assert item.content.data == b"test_data"

    def test_rename_works_with_multiple_names(self):
        content = "This is page content"
        meta = {NAME: ["First", "Second", "Third"], CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}
        update_item("Page", meta, content)

        item = Item.create("Second")
        item.rename(["New name", "First", "Third"], comment="renamed")

        item1 = Item.create("First")
        assert item1.name == "First"
        assert "First" in item1.meta[NAME]
        assert "Third" in item1.meta[NAME]
        assert "New name" in item1.meta[NAME]
        assert item1.meta[CONTENTTYPE] == "text/x.moin.wiki;charset=utf-8"
        assert item1.content.data == content.encode()

        item2 = Item.create("New name")
        assert item2.name == "New name"
        assert "First" in item2.meta[NAME]
        assert "Third" in item2.meta[NAME]
        assert "New name" in item2.meta[NAME]
        assert item2.meta[CONTENTTYPE] == "text/x.moin.wiki;charset=utf-8"
        assert item2.content.data == content.encode()

        item3 = Item.create("Third")
        assert item3.name == "Third"
        assert "First" in item3.meta[NAME]
        assert "Third" in item3.meta[NAME]
        assert "New name" in item3.meta[NAME]
        assert item3.meta[CONTENTTYPE] == "text/x.moin.wiki;charset=utf-8"
        assert item3.content.data == content.encode()

        assert item1.rev.revid == item2.rev.revid == item3.rev.revid

        item4 = Item.create("Second")
        assert item4.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT

    def test_rename_recursion(self):
        update_item("Page", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Page 1")
        update_item("Page/Child", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "this is child")
        update_item("Page/Child/Another", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "another child")

        item = Item.create("Page")
        item.rename("Renamed_Page", comment="renamed")

        # items at original name and its contents after renaming
        item = Item.create("Page")
        assert item.name == "Page"
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT
        item = Item.create("Page/Child")
        assert item.name == "Page/Child"
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT
        item = Item.create("Page/Child/Another")
        assert item.name == "Page/Child/Another"
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT

        # item at new name and its contents after renaming
        item = Item.create("Renamed_Page")
        assert item.name == "Renamed_Page"
        assert item.meta[NAME_OLD] == ["Page"]
        assert item.meta[COMMENT] == "renamed"
        assert item.content.data == b"Page 1"

        item = Item.create("Renamed_Page/Child")
        assert item.name == "Renamed_Page/Child"
        assert item.meta[NAME_OLD] == ["Page/Child"]
        assert item.meta[COMMENT] == "renamed"
        assert item.content.data == b"this is child"

        item = Item.create("Renamed_Page/Child/Another")
        assert item.name == "Renamed_Page/Child/Another"
        assert item.meta[NAME_OLD] == ["Page/Child/Another"]
        assert item.meta[COMMENT] == "renamed"
        assert item.content.data == b"another child"

    def test_rename_recursion_with_multiple_names_and_children(self):
        update_item("Foo", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8", NAME: ["Other", "Page", "Foo"]}, "Parent")
        update_item("Page/Child", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Child of Page")
        update_item("Other/Child2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Child of Other")
        update_item(
            "Another", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8", NAME: ["Another", "Page/Second"]}, "Both"
        )
        update_item("Page/Second/Child", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Child of Second")
        update_item("Another/Child", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Child of Another")

        item = Item.create("Page")

        item.rename(["Renamed", "Other"], comment="renamed")

        assert Item.create("Page/Child").meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT
        assert Item.create("Renamed/Child").content.data == b"Child of Page"
        assert Item.create("Page/Second").meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT
        assert Item.create("Renamed/Second").content.data == b"Both"
        assert Item.create("Another").content.data == b"Both"
        assert Item.create("Page/Second/Child").meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT
        assert Item.create("Renamed/Second/Child").content.data == b"Child of Second"
        assert Item.create("Other/Child2").content.data == b"Child of Other"
        assert Item.create("Another/Child").content.data == b"Child of Another"

    def test_delete(self):
        name = "Test_Item2"
        contenttype = "text/plain;charset=utf-8"
        data = "test_data"
        meta = {"test_key": "test_value", CONTENTTYPE: contenttype}
        comment = "saved it"
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        # item and its contents before deleting
        item = Item.create(name)
        assert item.name == "Test_Item2"
        assert item.meta[COMMENT] == "saved it"
        item.delete("deleted")
        # item and its contents after deletion
        item = Item.create(name)
        assert item.name == "Test_Item2"
        # this should be a fresh, new item, NOT the stuff we deleted:
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT

    def test_delete_multi_name_multi_subs(self):
        """
        Parent name is [aaa,bbbb,ccccc], subs are aaa/aaa, bbbb/bbbb. Deleting ccccc deletes all.
        """
        contenttype = "text/plain;charset=utf-8"
        data = "test_data"
        meta = {"test_key": "test_value", CONTENTTYPE: contenttype}
        comment = "saved it"
        item = Item.create("aaa")
        item._save(meta, data, comment=comment)

        # rename
        item = Item.create("aaa")
        item.rename(["aaa", "bbbb", "ccccc"], comment="renamed")

        # create subs aaa/aaa and bbbb/bbbb
        asub = Item.create("aaa/aaa")
        asub._save(meta, data, comment="aaa/aaa created")
        bsub = Item.create("bbbb/bbbb")
        bsub._save(meta, data, comment="bbbb/bbbb created")

        # item and its contents before deleting
        item = Item.create("ccccc")
        assert item.name == "ccccc"
        assert item.meta[COMMENT] == "renamed"
        item.delete("deleted ccccc")

        # all three alias names and both subitems are deleted
        item = Item.create("aaa")
        assert item.name == "aaa"
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT

        item = Item.create("bbbb")
        assert item.name == "bbbb"
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT

        item = Item.create("ccccc")
        assert item.name == "ccccc"
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT

        item = Item.create("aaa/aaa")
        assert item.name == "aaa/aaa"
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT

        item = Item.create("bbbb/bbbb")
        assert item.name == "bbbb/bbbb"
        assert item.meta[CONTENTTYPE] == CONTENTTYPE_NONEXISTENT

    def test_revert(self):
        name = "Test_Item"
        contenttype = "text/plain;charset=utf-8"
        data = "test_data"
        meta = {"test_key": "test_value", CONTENTTYPE: contenttype}
        comment = "saved it"
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        item = Item.create(name)
        item.revert("revert")
        item = Item.create(name)
        assert item.meta[ACTION] == ACTION_REVERT

    def test_modify(self):
        name = "Test_Item"
        contenttype = "text/plain;charset=utf-8"
        data = "test_data"
        meta = {"test_key": "test_value", CONTENTTYPE: contenttype}
        comment = "saved it"
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        item = Item.create(name)
        assert item.name == "Test_Item"
        assert item.meta["test_key"] == "test_value"
        # modify
        another_data = "another_test_data"
        another_meta = {"another_test_key": "another_test_value", CONTENTTYPE: contenttype}
        item.modify(another_meta, another_data)
        item = Item.create(name)
        assert item.name == "Test_Item"
        with pytest.raises(KeyError):
            item.meta["test_key"]
        assert item.meta["another_test_key"] == another_meta["another_test_key"]
        assert item.content.data == another_data.encode()
        # add/update meta
        another_meta = {"test_key": "test_value", "another_test_key": "another_test_value", CONTENTTYPE: contenttype}
        item.modify(another_meta, another_data)
        item = Item.create(name)
        update_meta = {
            "another_test_key": "updated_test_value",
            "new_test_key": "new_test_value",
            "none_test_key": None,
            CONTENTTYPE: contenttype,
        }
        item.modify(another_meta, another_data, **update_meta)
        item = Item.create(name)
        assert item.name == "Test_Item"
        assert item.meta["test_key"] == another_meta["test_key"]
        assert item.meta["another_test_key"] == update_meta["another_test_key"]
        assert item.meta["new_test_key"] == update_meta["new_test_key"]
        assert "none_test_key" not in item.meta

    def test_trash(self):
        name = "trash_item_test"
        contenttype = "text/plain;charset=utf-8"
        data = "test_data"
        meta = {CONTENTTYPE: contenttype}
        item = Item.create(name)
        # save rev 0
        item._save(meta, data)
        item = Item.create(name)
        assert not item.meta.get(TRASH)

        meta = dict(item.meta)
        meta[NAME] = []
        # save new rev with no names.
        item._save(meta, data, delete=True)
        new_name = "@itemid/" + item.meta[ITEMID]
        item = Item.create(new_name)
        assert item.meta[TRASH]

        new_meta = {NAME: ["foobar", "buz"], CONTENTTYPE: contenttype}
        item._save(new_meta, data)
        item = Item.create("foobar")

        item.delete("Deleting foobar.")
        item = Item.create("buz")
        assert not item.meta.get(TRASH)

        # Also delete the only name left.
        item.delete("Moving item to trash.")
        item = Item.create(new_name)
        assert item.meta[TRASH]


coverage_modules = ["moin.items"]
