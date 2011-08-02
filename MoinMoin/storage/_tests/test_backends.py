# -*- coding: utf-8 -*-
# Copyright: 2008 MoinMoin:PawelPacana
# Copyright: 2008 MoinMoin:ChristopherDenter
# Copyright: 2008 MoinMoin:JohannesBerg
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Backend tests

    This module provides class for testing backends. This class tries
    to cover sane backend usage examples.

    This class should be inherited by descendant backend test classes.
    Add tests general for all backends here. Your backend-specific tests
    put in class inherited from this one.
"""


import py.test, re, time

from flask import g as flaskg

from MoinMoin.storage import Item, NewRevision
from MoinMoin.storage.backends import memory
from MoinMoin.storage.error import NoSuchItemError, ItemAlreadyExistsError, NoSuchRevisionError, RevisionAlreadyExistsError
from MoinMoin.storage import terms
from MoinMoin.config import SIZE

item_names = (u"quite_normal",
              u"äöüßłóąćółąńśćżź",
              u"with space",
              u"name#special(characters?.\,",
              u"very_long_name_" * 100 + u"ending_1",
              u"very_long_name_" * 100 + u"ending_2", )

invalid_names = (42, {}, (1, ), [1], )

class BackendTest(object):
    """
    Generic class for backend tests.

    Creates a new backend for each test so they can assume to be
    sandboxed.
    """

    valid_names = item_names
    invalid_names = invalid_names

    def setup_method(self, method):
        self.backend = self.create_backend()

    def teardown_method(self, method):
        self.kill_backend()
        self.backend = None

    def create_rev_item_helper(self, name):
        item = self.backend.create_item(name)
        item.create_revision(0)
        item.commit()
        return item

    def create_meta_item_helper(self, name):
        item = self.backend.create_item(name)
        item.change_metadata()
        item.publish_metadata()
        return item

    def get_item_check(self, name):
        item = self.backend.get_item(name)
        assert item.name == name

    def rename_item_check(self, old_name, new_name):
        item = self.backend.get_item(old_name)
        item.rename(new_name)
        assert item.name == new_name
        assert self.backend.has_item(new_name)
        assert not self.backend.has_item(old_name)

    def test_create_get_rename_get_rev_item(self):
        def create_rev_item(name):
            item = self.backend.create_item(name)
            assert item.name == name
            item.create_revision(0)
            item.commit()
            assert self.backend.has_item(name)

        for num, item_name in enumerate(self.valid_names):
            yield create_rev_item, item_name
            yield self.get_item_check, item_name
            new_name = u"renamed_revitem_%d" % num
            yield self.rename_item_check, item_name, new_name
            yield self.get_item_check, new_name

    def test_create_get_rename_get_meta_item(self):
        def create_meta_item(name):
            item = self.backend.create_item(name)
            assert item.name == name
            item.change_metadata()
            item.publish_metadata()
            assert self.backend.has_item(name)

        for num, item_name in enumerate(self.valid_names):
            yield create_meta_item, item_name
            yield self.get_item_check, item_name
            new_name = u"renamed_revitem_%d" % num
            yield self.rename_item_check, item_name, new_name
            yield self.get_item_check, new_name

    def test_item_rename_to_existing(self):
        item1 = self.create_rev_item_helper(u"fresh_item")
        item2 = self.create_rev_item_helper(u"try to rename")
        py.test.raises(ItemAlreadyExistsError, item1.rename, item2.name)

    def rename_item_invalid_name(self, name, newname):
        item = self.backend.create_item(name)
        py.test.raises(TypeError, item.rename, newname)

    def test_item_rename_to_invalid(self):
        for num, invalid_name in enumerate(self.invalid_names):
            yield self.rename_item_invalid_name, u"item_%s" % num, invalid_name

    def test_item_rename_threesome(self):
        item1 = self.create_rev_item_helper(u"item1")
        item2 = self.create_rev_item_helper(u"item2")
        item1.create_revision(1)
        item1.commit()
        item2.rename(u"item3")
        item1.rename(u"item2")
        assert len(item1.list_revisions()) == 2

    def create_item_invalid_name(self, name):
        py.test.raises(TypeError, self.backend.create_item, name)

    def test_create_item_wrong_itemname(self):
        for item_name in self.invalid_names:
            yield self.create_item_invalid_name, item_name

    def test_create_order(self):
        item1 = self.backend.create_item(u'1')
        item2 = self.backend.create_item(u'2')
        revision1 = item1.create_revision(0)
        revision2 = item2.create_revision(0)
        revision1.write('1')
        revision2.write('2')
        item2.commit()
        item1.commit()
        item1 = self.backend.get_item(u'1')
        item2 = self.backend.get_item(u'2')
        revision1 = item1.get_revision(0)
        revision2 = item2.get_revision(0)
        assert revision1.read() == '1'
        assert revision2.read() == '2'

    def test_create_rev_item_again(self):
        self.create_rev_item_helper(u"item1")
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, u"item1")

    def test_create_meta_item_again(self):
        self.create_meta_item_helper(u"item2")
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, u"item2")

    def test_get_item_that_doesnt_exist(self):
        py.test.raises(NoSuchItemError, self.backend.get_item, u"i_do_not_exist")

    def test_has_item(self):
        self.create_rev_item_helper(u"versioned")
        self.create_meta_item_helper(u"unversioned")
        assert self.backend.has_item(u"versioned")
        assert self.backend.has_item(u"unversioned")

    def test_has_item_that_doesnt_exist(self):
        assert not self.backend.has_item(u"i_do_not_exist")

    def test_search_simple(self):
        for name in [u"songlist", u"song lyric", u"odd_SONG_item"]:
            self.create_rev_item_helper(name)
        self.create_meta_item_helper(u"new_song_player")
        query_string = u"song"
        query = terms.Name(query_string, True)
        for num, item in enumerate(self.backend.search_items(query)):
            assert item.name.find(query_string) != -1
        assert num == 2

    def test_search_better(self):
        self.create_rev_item_helper(u'abcde')
        self.create_rev_item_helper(u'abcdef')
        self.create_rev_item_helper(u'abcdefg')
        self.create_rev_item_helper(u'abcdefgh')

        def _test_search(term, expected):
            found = list(self.backend.search_items(term))
            assert len(found) == expected

        # must be /part/ of the name
        yield _test_search, terms.Name(u'AbCdEf', False), 3
        yield _test_search, terms.Name(u'AbCdEf', True), 0
        yield _test_search, terms.Name(u'abcdef', True), 3
        yield _test_search, terms.NameRE(re.compile(u'abcde.*')), 4
        yield _test_search, terms.NameFn(lambda n: n == u'abcdef'), 1

    def test_iteritems_1(self):
        for num in range(10, 20):
            self.create_rev_item_helper(u"item_" + str(num).zfill(2))
        for num in range(10):
            self.create_meta_item_helper(u"item_" + str(num).zfill(2))
        itemlist = sorted([item.name for item in self.backend.iteritems()])
        for num, itemname in enumerate(itemlist):
            assert itemname == u"item_" + str(num).zfill(2)
        assert len(itemlist) == 20

    def test_iteritems_2(self):
        self.create_rev_item_helper(u'abcdefghijklmn')
        count = 0
        for item in self.backend.iteritems():
            count += 1
        assert count > 0

    def test_iteritems_3(self):
        self.create_rev_item_helper(u"without_meta")
        self.create_rev_item_helper(u"with_meta")
        item = self.backend.get_item(u"with_meta")
        item.change_metadata()
        item[u"meta"] = u"data"
        item.publish_metadata()
        itemlist = [item for item in self.backend.iteritems()]
        assert len(itemlist) == 2

    def test_existing_item_create_revision(self):
        self.create_rev_item_helper(u"existing")
        item = self.backend.get_item(u"existing")
        old_rev = item.get_revision(-1)
        rev = item.create_revision(old_rev.revno + 1)
        item.rollback()
        rev = item.get_revision(-1)
        old_keys = old_rev.keys()
        new_keys = rev.keys()
        old_keys.sort()
        new_keys.sort()
        assert old_keys == new_keys
        for key, value in old_rev.iteritems():
            assert rev[key] == value
        assert old_rev.read() == rev.read()

    def test_new_item_create_revision(self):
        item = self.backend.create_item(u'internal')
        rev = item.create_revision(0)
        item.rollback()
        assert not self.backend.has_item(item.name)

    def test_item_commit_revision(self):
        item = self.backend.create_item(u"item#11")
        rev = item.create_revision(0)
        rev.write("python rocks")
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == "python rocks"

    def test_item_writing_data_multiple_times(self):
        item = self.backend.create_item(u"multiple")
        rev = item.create_revision(0)
        rev.write("Alle ")
        rev.write("meine ")
        rev.write("Entchen")
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == "Alle meine Entchen"

    def test_item_write_seek_read(self):
        item = self.backend.create_item(u"write_seek_read")
        rev = item.create_revision(0)
        write_data = "some data"
        rev.write(write_data)
        rev.seek(0)
        read_data = rev.read()
        assert read_data == write_data
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == write_data

    def test_item_seek_tell_read(self):
        item = self.backend.create_item(u"write_seek_read")
        rev = item.create_revision(0)
        write_data = "0123456789"
        rev.write(write_data)
        rev.seek(0)
        assert rev.tell() == 0
        read_data = rev.read()
        assert read_data == write_data
        rev.seek(4)
        assert rev.tell() == 4
        read_data = rev.read()
        assert read_data == write_data[4:]
        item.commit()
        rev = item.get_revision(0)
        rev.seek(0)
        assert rev.tell() == 0
        read_data = rev.read()
        assert read_data == write_data
        rev.seek(4)
        assert rev.tell() == 4
        read_data = rev.read()
        assert read_data == write_data[4:]

    def test_item_reading_chunks(self):
        item = self.backend.create_item(u"slices")
        rev = item.create_revision(0)
        rev.write("Alle meine Entchen")
        item.commit()
        rev = item.get_revision(0)
        chunk = rev.read(1)
        data = ""
        while chunk != "":
            data += chunk
            chunk = rev.read(1)
        assert data == "Alle meine Entchen"

    def test_item_reading_negative_chunk(self):
        item = self.backend.create_item(u"negative_chunk")
        rev = item.create_revision(0)
        rev.write("Alle meine Entchen" * 10)
        item.commit()
        rev = item.get_revision(0)
        assert rev.read(-1) == "Alle meine Entchen" * 10
        rev.seek(0)
        assert rev.read(-123) == "Alle meine Entchen" * 10

    def test_seek_and_tell(self):
        item = self.backend.create_item(u"seek&tell")
        rev = item.create_revision(0)
        data = "wilhelm tell seekfried what time it is"
        rev.write(data)
        item.commit()

        rev = item.get_revision(0)
        offset = 5

        # absolute
        rev.seek(offset)
        assert rev.tell() == offset
        assert rev.read() == data[offset:]

        # relative
        rev.seek(offset)
        rev.seek(offset, 1)
        assert rev.tell() == 2 * offset
        assert rev.read() == data[2*offset:]

        # relative to EOF
        rev.seek(-offset, 2)
        assert rev.tell() == len(data) - offset
        assert rev.read() == data[-offset:]

    def test_item_get_revision(self):
        item = self.backend.create_item(u"item#12")
        rev = item.create_revision(0)
        rev.write("jefferson airplane rocks")
        item.commit()
        another_rev = item.get_revision(0)
        assert another_rev.read() == "jefferson airplane rocks"

    def test_item_next_revno(self):
        item = self.backend.create_item(u"next_revno")
        assert item.next_revno == 0
        item.create_revision(item.next_revno).write("foo")
        item.commit()
        assert item.next_revno == 1

    def test_item_list_revisions_with_revmeta_changes(self):
        item = self.backend.create_item(u"item_13")
        for revno in range(0, 10):
            rev = item.create_revision(revno)
            rev[u"revno"] = u"%s" % revno
            item.commit()
        assert item.list_revisions() == range(0, 10)

    def test_item_list_revisions_with_revdata_changes(self):
        item = self.backend.create_item(u"item_13")
        for revno in range(0, 10):
            rev = item.create_revision(revno)
            rev.write("%s" % revno)
            item.commit()
        assert item.list_revisions() == range(0, 10)

    def test_item_list_revisions_without_changes(self):
        item = self.backend.create_item(u"item_13")
        for revno in range(0, 10):
            item.create_revision(revno)
            item.commit()
        assert item.list_revisions() == range(0, 10)

    def test_item_list_revisions_equality(self):
        item = self.backend.create_item(u"new_item_15")
        revs_before = item.list_revisions()
        rev = item.create_revision(0)
        assert item.list_revisions() == revs_before
        item.rollback()

    def test_item_list_revisions_equality_nonempty_revlist(self):
        item = self.backend.create_item(u"new_item_16")
        rev = item.create_revision(0)
        rev.write("something interesting")
        item.commit()
        revs_before = item.list_revisions()
        rev2 = item.create_revision(1)
        assert item.list_revisions() == revs_before
        item.rollback()

    def test_item_list_revisions_without_committing(self):
        item = self.backend.create_item(u"new_item_14")
        assert item.list_revisions() == []

    def test_mixed_commit_metadata1(self):
        item = self.backend.create_item(u'mixed1')
        item.create_revision(0)
        py.test.raises(RuntimeError, item.change_metadata)
        item.rollback()

    def test_mixed_commit_metadata2(self):
        item = self.backend.create_item(u'mixed2')
        item.change_metadata()
        py.test.raises(RuntimeError, item.create_revision, 0)

    def test_item_metadata_change_and_publish(self):
        item = self.backend.create_item(u"test item metadata change")
        item.change_metadata()
        item[u"creator"] = u"Vincent van Gogh"
        item.publish_metadata()
        item2 = self.backend.get_item(u"test item metadata change")
        assert item2[u"creator"] == u"Vincent van Gogh"

    def test_item_metadata_invalid_change(self):
        item = self.backend.create_item(u"test item metadata invalid change")
        try:
            item[u"this should"] = "FAIL!"
            assert False
        except AttributeError:
            pass

    def test_item_metadata_without_publish(self):
        item = self.backend.create_item(u"test item metadata invalid change")
        item.change_metadata()
        item[u"change but"] = u"don't publish"
        py.test.raises(NoSuchItemError, self.backend.get_item, "test item metadata invalid change")

    def test_item_create_existing_mixed_1(self):
        item1 = self.backend.create_item(u'existing now 0')
        item1.change_metadata()
        item2 = self.backend.create_item(u'existing now 0')
        item1.publish_metadata()
        item2.create_revision(0)
        py.test.raises(ItemAlreadyExistsError, item2.commit)

    def test_item_create_existing_mixed_2(self):
        item1 = self.backend.create_item(u'existing now 0')
        item1.change_metadata()
        item2 = self.backend.create_item(u'existing now 0')
        item2.create_revision(0)
        item2.commit()
        py.test.raises(ItemAlreadyExistsError, item1.publish_metadata)

    def test_item_multiple_change_metadata_after_create(self):
        name = u"foo"
        item1 = self.backend.create_item(name)
        item2 = self.backend.create_item(name)
        item1.change_metadata()
        item2.change_metadata()
        item1[u"a"] = u"a"
        item2[u"a"] = u"b"
        item1.publish_metadata()
        py.test.raises(ItemAlreadyExistsError, item2.publish_metadata)
        item = self.backend.get_item(name)
        assert item[u"a"] == u"a"

    def test_existing_item_change_metadata(self):
        self.create_meta_item_helper(u"existing now 2")
        item = self.backend.get_item(u'existing now 2')
        item.change_metadata()
        item[u'asdf'] = u'b'
        item.publish_metadata()
        item = self.backend.get_item(u'existing now 2')
        assert item[u'asdf'] == u'b'

    def test_metadata(self):
        self.create_rev_item_helper(u'no metadata')
        item = self.backend.get_item(u'no metadata')
        py.test.raises(KeyError, item.__getitem__, u'asdf')

    def test_revision(self):
        self.create_meta_item_helper(u'no revision')
        item = self.backend.get_item(u'no revision')
        py.test.raises(NoSuchRevisionError, item.get_revision, -1)

    def test_create_revision_change_meta(self):
        item = self.backend.create_item(u"double")
        rev = item.create_revision(0)
        rev[u"revno"] = u"0"
        item.commit()
        item.change_metadata()
        item[u"meta"] = u"data"
        item.publish_metadata()
        item = self.backend.get_item(u"double")
        assert item[u"meta"] == u"data"
        rev = item.get_revision(0)
        assert rev[u"revno"] == u"0"

    def test_create_revision_change_empty_meta(self):
        item = self.backend.create_item(u"double")
        rev = item.create_revision(0)
        rev[u"revno"] = u"0"
        item.commit()
        item.change_metadata()
        item.publish_metadata()
        item = self.backend.get_item(u"double")
        rev = item.get_revision(0)
        assert rev[u"revno"] == u"0"

    def test_change_meta_create_revision(self):
        item = self.backend.create_item(u"double")
        item.change_metadata()
        item[u"meta"] = u"data"
        item.publish_metadata()
        rev = item.create_revision(0)
        rev[u"revno"] = u"0"
        item.commit()
        item = self.backend.get_item(u"double")
        assert item[u"meta"] == u"data"
        rev = item.get_revision(0)
        assert rev[u"revno"] == u"0"

    def test_meta_after_rename(self):
        item = self.backend.create_item(u"re")
        item.change_metadata()
        item[u"previous_name"] = u"re"
        item.publish_metadata()
        item.rename(u"er")
        assert item[u"previous_name"] == u"re"

    def test_long_names_back_and_forth(self):
        item = self.backend.create_item(u"long_name_" * 100 + u"with_happy_end")
        item.create_revision(0)
        item.commit()
        assert self.backend.has_item(u"long_name_" * 100 + u"with_happy_end")
        item = self.backend.iteritems().next()
        assert item.name == u"long_name_" * 100 + u"with_happy_end"

    def test_revisions_after_rename(self):
        item = self.backend.create_item(u"first one")
        for revno in xrange(10):
            rev = item.create_revision(revno)
            rev[u"revno"] = unicode(revno)
            item.commit()
        assert item.list_revisions() == range(10)
        item.rename(u"second one")
        assert not self.backend.has_item(u"first one")
        assert self.backend.has_item(u"second one")
        item1 = self.backend.create_item(u"first_one")
        item1.create_revision(0)
        item1.commit()
        assert len(item1.list_revisions()) == 1
        item2 = self.backend.get_item(u"second one")
        assert item2.list_revisions() == range(10)
        for revno in xrange(10):
            rev = item2.get_revision(revno)
            assert rev[u"revno"] == unicode(revno)

    def test_concurrent_create_revision(self):
        self.create_rev_item_helper(u"concurrent")
        item1 = self.backend.get_item(u"concurrent")
        item2 = self.backend.get_item(u"concurrent")
        item1.create_revision(1)
        item2.create_revision(1)
        item1.commit()
        py.test.raises(RevisionAlreadyExistsError, item2.commit)

    def test_timestamp(self):
        tnow = int(time.time())
        item = self.backend.create_item(u'ts1')
        rev = item.create_revision(0)
        item.commit()
        item = self.backend.get_item(u'ts1')
        ts = item.get_revision(0).timestamp
        assert tnow <= ts <= ts + 60

    def test_size(self):
        item = self.backend.create_item(u'size1')
        rev = item.create_revision(0)
        rev.write('asdf')
        rev.write('asdf')
        item.commit()
        rev = item.get_revision(0)
        assert rev[SIZE] == 8

        for nrev in self.backend.history():
            assert nrev[SIZE] == 8

    def test_size_2(self):
        item = self.backend.create_item(u'size2')
        rev0 = item.create_revision(0)
        data0 = 'asdf'
        rev0.write(data0)
        item.commit()
        rev1 = item.create_revision(1)
        item.commit()
        rev1 = item.get_revision(1)
        assert rev1[SIZE] == 0
        rev0 = item.get_revision(0)
        assert rev0[SIZE] == len(data0)

    def test_various_revision_metadata_values(self):
        def test_value(value, no):
            item = self.backend.create_item(u'valid_values_%d' % no)
            rev = item.create_revision(0)
            key = u"key%d" % no
            rev[key] = value
            item.commit()
            rev = item.get_revision(0)
            assert rev[key] == value

        for no, value in enumerate(('string', 13, 42L, 3.14, 23+0j,
                                       ('1', 1, 1L, 1+0j, (1, ), ), u'ąłć', (u'ó', u'żźć'), )):
            yield test_value, value, no

    def test_history(self):
        order = [(u'first', 0, ), (u'second', 0, ), (u'first', 1, ), (u'a', 0), (u'child/my_subitem', 0) ]
        for name, revno in order:
            if revno == 0:
                item = self.backend.create_item(name)
            else:
                item = self.backend.get_item(name)
            item.create_revision(revno)
            item.commit()

            from MoinMoin.storage.backends import router, acl
            if isinstance(self.backend, (router.RouterBackend, acl.AclWrapperBackend)):
                # Revisions are created too fast for the rev's timestamp's granularity.
                # This only affects the RouterBackend because there several different
                # backends are used and no means for storing simultaneously created revs
                # in the correct order exists between backends. It affects AclWrapperBackend
                # tests as well because those use a RouterBackend internally for real-world-likeness.

                # XXX XXX
                # You may have realized that all the items above belong to the same backend so this shouldn't actually matter.
                # It does matter, however, once you consider that the RouterBackend uses the generic, slow history implementation.
                # This one uses iteritems and then sorts all the revisions itself, hence discarding any information of ordering
                # for simultaneously created revisions. If we just call history of that single backend directly, it works without
                # time.sleep. For n backends, however, you'd have to somehow merge the revisions into one generator again, thus
                # discarding that information again. Besides, that would be a costly operation. The ordering for simultaneosly
                # created revisions remains the same since it's based on tuple ordering. Better proposals welcome.
                import time
                time.sleep(1)

        for num, rev in enumerate(self.backend.history(reverse=False)):
            name, revno = order[num]
            assert rev.item.name == name
            assert rev.revno == revno

        order.reverse()
        for num, rev in enumerate(self.backend.history()):
            name, revno = order[num]
            assert rev.item.name == name
            assert rev.revno == revno

    # See history function in indexing.py for comments on why this test fails.
    @py.test.mark.xfail
    def test_history_size_after_rename(self):
        item = self.backend.create_item(u'first')
        item.create_revision(0)
        item.commit()
        item.rename(u'second')
        item.create_revision(1)
        item.commit()
        assert len([rev for rev in self.backend.history()]) == 2

    def test_destroy_item(self):
        itemname = u"I will be completely destroyed"
        rev_data = "I will be completely destroyed, too, hopefully"
        item = self.backend.create_item(itemname)
        rev = item.create_revision(0)
        rev.write(rev_data)
        item.commit()

        item.destroy()
        assert not self.backend.has_item(itemname)
        item_names = [item.name for item in self.backend.iteritems()]
        assert not itemname in item_names
        all_rev_data = [rev.read() for rev in self.backend.history()]
        assert not rev_data in all_rev_data

        for rev in self.backend.history():
            assert not rev.item.name == itemname
        for rev in self.backend.history(reverse=False):
            assert not rev.item.name == itemname


    def test_destroy_revision(self):
        itemname = u"I will see my children die :-("
        rev_data = "I will die!"
        persistent_rev = "I will see my sibling die :-("
        item = self.backend.create_item(itemname)
        rev = item.create_revision(0)
        rev.write(rev_data)
        item.commit()
        rev = item.create_revision(1)
        rev.write(persistent_rev)
        item.commit()
        assert item.list_revisions() == range(2)

        rev = item.get_revision(0)
        rev.destroy()
        assert item.list_revisions() == [1]
        assert self.backend.has_item(itemname)
        assert item.get_revision(-1).read() == persistent_rev

        third = "3rd revision"
        rev = item.create_revision(2)
        rev.write(third)
        item.commit()
        rev = item.get_revision(2)
        assert item.get_revision(-1).read() == third
        assert len(item.list_revisions()) == 2
        rev.destroy()
        assert len(item.list_revisions()) == 1
        last = item.get_revision(-1)
        assert last.revno == 1
        last_data = last.read()
        assert last_data != third
        assert last_data == persistent_rev

        for rev in self.backend.history():
            assert not (rev.item.name == itemname and rev.revno == 2)

    def test_clone_backend(self):
        src = flaskg.storage
        dst = memory.MemoryBackend()

        dollys_name = u"Dolly The Sheep"
        item = src.create_item(dollys_name)
        rev = item.create_revision(0)
        rev.write("maeh")
        rev[u'origin'] = u'reagenzglas'
        item.commit()

        brothers_name = u"Dolly's brother"
        item = src.create_item(brothers_name)
        item.change_metadata()
        item[u'no revisions'] = True
        item.publish_metadata()

        dst.clone(src, verbose=False)

        assert len(list(dst.iteritems())) == 2
        assert len(list(dst.history())) == 1
        assert dst.has_item(dollys_name)
        rev = dst.get_item(dollys_name).get_revision(0)
        data = rev.read()
        assert data == "maeh"
        meta = dict(rev.iteritems())
        assert u'origin' in meta
        assert meta[u'origin'] == u'reagenzglas'

        assert dst.has_item(brothers_name)
        item = dst.get_item(brothers_name)
        meta = dict(item.iteritems())
        assert u'no revisions' in meta
        assert meta[u'no revisions'] is True

    def test_iteritems_item_names_after_rename(self):
        item = self.backend.create_item(u'first')
        item.create_revision(0)
        item.commit()
        item.rename(u'second')
        item.create_revision(1)
        item.commit()
        # iteritems provides actual name
        items = [item for item in self.backend.iteritems()]
        assert len(items) == 1
        assert items[0].name == u'second'
        rev0 = items[0].get_revision(0)
        assert rev0.item.name == u'second'
        rev1 = items[0].get_revision(1)
        assert rev1.item.name == u'second'

    def test_iteritems_after_destroy(self):
        item = self.backend.create_item(u'first')
        item.create_revision(0)
        item.commit()
        item.create_revision(1)
        item.commit()
        assert len([item for item in self.backend.iteritems()]) == 1
        rev = item.get_revision(-1)
        rev.destroy()
        assert len([item for item in self.backend.iteritems()]) == 1
        item.destroy()
        assert len([item for item in self.backend.iteritems()]) == 0

    def test_history_item_names(self):
        item = self.backend.create_item(u'first')
        item.create_revision(0)
        item.commit()
        item.rename(u'second')
        item.create_revision(1)
        item.commit()
        revs_in_create_order = [rev for rev in self.backend.history(reverse=False)]
        assert revs_in_create_order[0].revno == 0
        assert revs_in_create_order[0].item.name == u'second'
        assert revs_in_create_order[1].revno == 1
        assert revs_in_create_order[1].item.name == u'second'


