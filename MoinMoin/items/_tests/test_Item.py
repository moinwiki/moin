# Copyright: 2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.items Tests
"""


import py

from flask import g as flaskg

from MoinMoin._tests import become_trusted
from MoinMoin.items import Item, ApplicationXTar, NonExistent, Binary, Text, Image, TransformableBitmapImage
from MoinMoin.config import CONTENTTYPE, ADDRESS, COMMENT, HOSTNAME, USERID, ACTION
from MoinMoin.conftest import init_test_app, deinit_test_app
from MoinMoin._tests import wikiconfig

class TestItem(object):
    def setup_method(self, method):
        # temporary hack till we get some cleanup mechanism for tests.  
        self.app, self.ctx = init_test_app(wikiconfig.Config)
        
    def teardown_method(self, method):
        deinit_test_app(self.app, self.ctx)     

    def testNonExistent(self):
        item = Item.create('DoesNotExist')
        assert isinstance(item, NonExistent)
        meta, data = item.meta, item.data
        assert meta == {CONTENTTYPE: 'application/x-nonexistent'}
        assert data == ''

    def testClassFinder(self):
        for contenttype, ExpectedClass in [
                ('application/x-foobar', Binary),
                ('text/plain', Text),
                ('text/plain;charset=utf-8', Text),
                ('image/tiff', Image),
                ('image/png', TransformableBitmapImage),
            ]:
            item = Item.create('foo', contenttype=contenttype)
            assert isinstance(item, ExpectedClass)

    def testCRUD(self):
        name = u'NewItem'
        contenttype = 'text/plain;charset=utf-8'
        data = 'foobar'
        meta = dict(foo='bar')
        comment = u'saved it'
        become_trusted()
        item = Item.create(name)
        # save rev 0
        item._save(meta, data, contenttype=contenttype, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data
        assert item.rev.revno == 0

        data = rev1_data = data * 10000
        comment = comment + u' again'
        # save rev 1
        item._save(meta, data, contenttype=contenttype, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data
        assert item.rev.revno == 1

        data = ''
        comment = 'saved empty data'
        # save rev 2 (auto delete)
        item._save(meta, data, contenttype=contenttype, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data
        assert item.rev.revno == 2

        # access old revision
        item = Item.create(name, rev_no=1)
        assert item.data == rev1_data

    def testIndex(self):
        # create a toplevel and some sub-items
        basename = u'Foo'
        for name in ['', '/ab', '/cd/ef', '/gh', '/ij/kl', ]:
            item = Item.create(basename + name)
            item._save({}, "foo", contenttype='text/plain;charset=utf-8')

        # check index
        baseitem = Item.create(basename)
        index = baseitem.get_index()
        assert index == [(u'Foo/ab', u'ab', 'text/plain;charset=utf-8'),
                         (u'Foo/cd/ef', u'cd/ef', 'text/plain;charset=utf-8'),
                         (u'Foo/gh', u'gh', 'text/plain;charset=utf-8'),
                         (u'Foo/ij/kl', u'ij/kl', 'text/plain;charset=utf-8'),
                        ]
        flat_index = baseitem.flat_index()
        assert flat_index == [(u'Foo/ab', u'ab', 'text/plain;charset=utf-8'),
                              (u'Foo/gh', u'gh', 'text/plain;charset=utf-8'),
                             ]


class TestTarItems(object):
    """
    tests for the container items
    """
    def setup_method(self, method):
        # temporary hack till we get some cleanup mechanism for tests.  
        self.app, self.ctx = init_test_app(wikiconfig.Config)
        
    def teardown_method(self, method):
        deinit_test_app(self.app, self.ctx)     

    def testCreateContainerRevision(self):
        """
        creates a container and tests the content saved to the container
        """
        item_name = u'ContainerItem1'
        item = Item.create(item_name, contenttype='application/x-tar')
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = set(['example1.txt', 'example2.txt'])
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)
        item.put_member('example2.txt', filecontent, content_length, expected_members=members)

        item = Item.create(item_name, contenttype='application/x-tar')
        tf_names = set(item.list_members())
        assert tf_names == members
        assert item.get_member('example1.txt').read() == filecontent

    def testRevisionUpdate(self):
        """
        creates two revisions of a container item
        """
        item_name = u'ContainerItem2'
        item = Item.create(item_name, contenttype='application/x-tar')
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = set(['example1.txt'])
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)
        filecontent = 'AAAABBBB'
        content_length = len(filecontent)
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)

        item = flaskg.storage.get_item(item_name)
        assert item.next_revno == 2

        item = Item.create(item_name, contenttype='application/x-tar')
        assert item.get_member('example1.txt').read() == filecontent

coverage_modules = ['MoinMoin.items']

