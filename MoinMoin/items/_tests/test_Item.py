"""
    MoinMoin - MoinMoin.items Tests

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from flask import flaskg

from MoinMoin._tests import become_trusted
from MoinMoin.items import Item, ApplicationXTar, NonExistent, Binary, Text, Image, TransformableBitmapImage, \
                           MIMETYPE, ADDRESS, COMMENT, HOSTNAME, USERID, ACTION

class TestItem(object):
    def testNonExistent(self):
        item = Item.create('DoesNotExist')
        assert isinstance(item, NonExistent)
        meta, data = item.meta, item.data
        assert meta == {MIMETYPE: 'application/x-nonexistent'}
        assert data == ''

    def testClassFinder(self):
        for mimetype, ExpectedClass in [
                ('application/x-foobar', Binary),
                ('text/plain', Text),
                ('image/tiff', Image),
                ('image/png', TransformableBitmapImage),
            ]:
            item = Item.create('foo', mimetype=mimetype)
            assert isinstance(item, ExpectedClass)

    def testCRUD(self):
        name = u'NewItem'
        mimetype = 'text/plain'
        data = 'foobar'
        meta = dict(foo='bar')
        comment = u'saved it'
        become_trusted()
        item = Item.create(name)
        # save rev 0
        item._save(meta, data, mimetype=mimetype, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[MIMETYPE] == mimetype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data
        assert item.rev.revno == 0

        data = rev1_data = data * 10000
        comment = comment + u' again'
        # save rev 1
        item._save(meta, data, mimetype=mimetype, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[MIMETYPE] == mimetype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data
        assert item.rev.revno == 1

        data = ''
        comment = 'saved empty data'
        # save rev 2 (auto delete)
        item._save(meta, data, mimetype=mimetype, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[MIMETYPE] == mimetype
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
            item._save({}, "foo", mimetype='text/plain')

        # check index
        baseitem = Item.create(basename)
        index = baseitem.get_index()
        assert index == [(u'Foo/ab', u'ab', 'text/plain'),
                         (u'Foo/cd/ef', u'cd/ef', 'text/plain'),
                         (u'Foo/gh', u'gh', 'text/plain'),
                         (u'Foo/ij/kl', u'ij/kl', 'text/plain'),
                        ]
        flat_index = baseitem.flat_index()
        assert flat_index == [(u'Foo/ab', u'ab', 'text/plain'),
                              (u'Foo/gh', u'gh', 'text/plain'),
                             ]


class TestTarItems(object):
    """
    tests for the container items
    """
    def testCreateContainerRevision(self):
        """
        creates a container and tests the content saved to the container
        """
        item_name = u'ContainerItem1'
        item = Item.create(item_name, mimetype='application/x-tar')
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = set(['example1.txt', 'example2.txt'])
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)
        item.put_member('example2.txt', filecontent, content_length, expected_members=members)

        item = Item.create(item_name, mimetype='application/x-tar')
        tf_names = set(item.list_members())
        assert tf_names == members
        assert item.get_member('example1.txt').read() == filecontent

    def testRevisionUpdate(self):
        """
        creates two revisions of a container item
        """
        item_name = u'ContainerItem2'
        item = Item.create(item_name, mimetype='application/x-tar')
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = set(['example1.txt'])
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)
        filecontent = 'AAAABBBB'
        content_length = len(filecontent)
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)

        item = flaskg.storage.get_item(item_name)
        assert item.next_revno == 2

        item = Item.create(item_name, mimetype='application/x-tar')
        assert item.get_member('example1.txt').read() == filecontent

coverage_modules = ['MoinMoin.items']

