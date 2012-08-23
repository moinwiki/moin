# Copyright: 2012 MoinMoin:PavelSviderski
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.items.blog Tests
"""

import re

from flask import url_for

from MoinMoin._tests import become_trusted, update_item
from MoinMoin.items import Item
from MoinMoin.config import CONTENTTYPE, ITEMTYPE, PTIME, ACL, TAGS
from MoinMoin.items.blog import ITEMTYPE_BLOG, ITEMTYPE_BLOG_ENTRY
from MoinMoin.items.blog import Blog, BlogEntry


class TestView(object):
    def _test_view(self, item_name, req_args={}, data_tokens=[], exclude_data_tokens=[], regex=None):
        with self.app.test_client() as c:
            rv = c.get(url_for('frontend.show_item', item_name=item_name, **req_args))
            for data in data_tokens:
                assert data in rv.data
            for data in exclude_data_tokens:
                assert data not in rv.data
            if regex:
                assert regex.search(rv.data)


class TestBlog(TestView):
    NO_ENTRIES_MSG = u"There are no entries"

    name = u'NewBlogItem'
    contenttype = u'text/x.moin.wiki'
    data = u"This is the header item of this blog"
    meta = {CONTENTTYPE: contenttype, ITEMTYPE: ITEMTYPE_BLOG}
    comment = u'saved it'
    entries = [{'name': name + u'/NewBlogEntryItem1', 'data': u"First blog entry"},
               {'name': name + u'/NewBlogEntryItem2', 'data': u"Second blog entry"},
               {'name': name + u'/NewBlogEntryItem3', 'data': u"Third blog entry"},
               {'name': name + u'/NewBlogEntryItem4', 'data': u"Fourth blog entry"}, ]
    entry_meta = {CONTENTTYPE: contenttype, ITEMTYPE: ITEMTYPE_BLOG_ENTRY}

    def _publish_entry(self, entry, ptime, acl=None):
        meta = self.entry_meta.copy()
        meta[PTIME] = ptime
        if acl is not None:
            meta[ACL] = acl
        update_item(entry['name'], meta, entry['data'])

    def test_create(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # check save result
        item = Item.create(self.name)
        assert isinstance(item, Blog)
        assert item.itemtype == ITEMTYPE_BLOG
        assert item.meta[CONTENTTYPE] == self.contenttype

    def test_do_show_empty(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # empty blog page without any entries
        data_tokens = [self.data, self.NO_ENTRIES_MSG, ]
        self._test_view(self.name, data_tokens=data_tokens)

    def test_do_show_entries(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # store some unpublished entries
        for entry in self.entries:
            item = Item.create(entry['name'], itemtype=ITEMTYPE_BLOG_ENTRY)
            item._save(self.entry_meta, entry['data'], comment=self.comment)
        # still empty blog
        data_tokens = [self.data, self.NO_ENTRIES_MSG, ]
        self._test_view(self.name, data_tokens=data_tokens)
        # publish the first three entries, ptime value is a UNIX timestamp
        self._publish_entry(self.entries[0], ptime=1000)
        self._publish_entry(self.entries[1], ptime=3000)
        self._publish_entry(self.entries[2], ptime=2000)
        # the blog is not empty and the 4th entry is not published
        exclude_data_tokens = [self.NO_ENTRIES_MSG, self.entries[3]['data'], ]
        # blog entries are published in reverse order relative to their PTIMEs
        ordered_data = [self.data,
                        self.entries[1]['data'],
                        self.entries[2]['data'],
                        self.entries[0]['data'], ]
        regex = re.compile(r'{0}.*{1}.*{2}.*{3}'.format(*ordered_data), re.DOTALL)
        self._test_view(self.name, exclude_data_tokens=exclude_data_tokens, regex=regex)

    def test_filter_by_tag(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # publish some entries with tags
        entries_meta = [{ITEMTYPE: ITEMTYPE_BLOG_ENTRY, PTIME: 1000, TAGS: [u'foo', u'bar', u'moin', ]},
                        {ITEMTYPE: ITEMTYPE_BLOG_ENTRY, PTIME: 3000, TAGS: [u'foo', u'bar', u'baz', ]},
                        {ITEMTYPE: ITEMTYPE_BLOG_ENTRY, PTIME: 2000, TAGS: [u'baz', u'moin', ]}, ]
        for i in xrange(len(entries_meta)):
            entry = self.entries[i]
            entry_meta = entries_meta[i]
            item = Item.create(entry['name'], itemtype=ITEMTYPE_BLOG_ENTRY)
            item._save(entry_meta, entry['data'], comment=self.comment)
        # filter by non-existent tag 'non-existent'
        data_tokens = [self.data, self.NO_ENTRIES_MSG, ]
        exclude_data_tokens = [self.entries[0]['data'], self.entries[1]['data'], self.entries[2]['data'], ]
        self._test_view(self.name, req_args={u'tag': u'non-existent'}, data_tokens=data_tokens, exclude_data_tokens=exclude_data_tokens)
        # filter by tag 'moin'
        exclude_data_tokens = [self.NO_ENTRIES_MSG, self.entries[1]['data'], ]
        ordered_data = [self.data,
                        self.entries[2]['data'],
                        self.entries[0]['data'], ]
        regex = re.compile(r'{0}.*{1}.*{2}'.format(*ordered_data), re.DOTALL)
        self._test_view(self.name, req_args={u'tag': u'moin'}, exclude_data_tokens=exclude_data_tokens, regex=regex)

    def test_filter_by_acls(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # store some unpublished entries
        for entry in self.entries:
            item = Item.create(entry['name'], itemtype=ITEMTYPE_BLOG_ENTRY)
            item._save(self.entry_meta, entry['data'], comment=self.comment)
        # publish the first three entries with specific ACLs
        # we are an "anonymous" user
        self._publish_entry(self.entries[0], ptime=1000, acl=u"anonymous:read")
        self._publish_entry(self.entries[1], ptime=3000, acl=u"anonymous:read")
        # specify no rights on the 3rd entry
        self._publish_entry(self.entries[2], ptime=2000, acl=u"anonymous:")
        # the blog is not empty and the 3rd entry is not displayed
        exclude_data_tokens = [self.NO_ENTRIES_MSG, self.entries[2]['data'], ]
        ordered_data = [self.data,
                        self.entries[1]['data'],
                        self.entries[0]['data'], ]
        regex = re.compile(r'{0}.*{1}.*{2}'.format(*ordered_data), re.DOTALL)
        self._test_view(self.name, exclude_data_tokens=exclude_data_tokens, regex=regex)


class TestBlogEntry(TestView):
    blog_name = u'NewBlogItem'
    contenttype = u'text/x.moin.wiki'
    blog_data = u"This is the header item of this blog"
    blog_meta = {CONTENTTYPE: contenttype, ITEMTYPE: ITEMTYPE_BLOG}
    comment = u'saved it'
    entry_name = blog_name + u'/NewBlogEntryItem'
    entry_data = u"Blog entry data"
    entry_meta = {CONTENTTYPE: contenttype, ITEMTYPE: ITEMTYPE_BLOG_ENTRY}

    def test_create(self):
        # create a blog item
        item = Item.create(self.blog_name, itemtype=ITEMTYPE_BLOG)
        item._save(self.blog_meta, self.blog_data, comment=self.comment)
        # create a blog entry item
        item = Item.create(self.entry_name, itemtype=ITEMTYPE_BLOG_ENTRY)
        item._save(self.entry_meta, self.entry_data, comment=self.comment)
        # check save result
        item = Item.create(self.entry_name)
        assert isinstance(item, BlogEntry)
        assert item.itemtype == ITEMTYPE_BLOG_ENTRY
        assert item.meta[CONTENTTYPE] == self.contenttype

    def test_do_show(self):
        # create a blog item
        item = Item.create(self.blog_name, itemtype=ITEMTYPE_BLOG)
        item._save(self.blog_meta, self.blog_data, comment=self.comment)
        # create a blog entry item
        item = Item.create(self.entry_name, itemtype=ITEMTYPE_BLOG_ENTRY)
        item._save(self.entry_meta, self.entry_data, comment=self.comment)

        data_tokens = [self.blog_data, self.entry_data, ]
        self._test_view(self.entry_name, data_tokens=data_tokens)
