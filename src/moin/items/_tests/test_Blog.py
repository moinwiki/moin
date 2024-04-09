# Copyright: 2012 MoinMoin:PavelSviderski
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.items.blog Tests
"""

import re

from datetime import datetime
from flask import url_for

from moin._tests import update_item
from moin.items import Item
from moin.constants.keys import CONTENTTYPE, ITEMTYPE, PTIME, ACL, TAGS
from moin.constants.misc import ANON
from moin.items.blog import ITEMTYPE_BLOG, ITEMTYPE_BLOG_ENTRY
from moin.items.blog import Blog, BlogEntry
from moin.themes import utctimestamp

import pytest


class TestView:
    @pytest.fixture(autouse=True)
    def set_self_app(self, app):
        self.app = app

    def _test_view(self, item_name, req_args={}, data_tokens=[], exclude_data_tokens=[], regex=None):
        with self.app.test_client() as c:
            rv = c.get(url_for("frontend.show_item", item_name=item_name, **req_args))
            rv_data = rv.data.decode()
            for data in data_tokens:
                assert data in rv_data
            for data in exclude_data_tokens:
                assert data not in rv_data
            if regex:
                assert regex.search(rv_data)


class TestBlog(TestView):
    NO_ENTRIES_MSG = "There are no entries"

    name = "NewBlogItem"
    contenttype = "text/x.moin.wiki;charset=utf-8"
    data = "This is the header item of this blog"
    meta = {CONTENTTYPE: contenttype, ITEMTYPE: ITEMTYPE_BLOG}
    comment = "saved it"
    entries = [
        {"name": name + "/NewBlogEntryItem1", "data": "First blog entry"},
        {"name": name + "/NewBlogEntryItem2", "data": "Second blog entry"},
        {"name": name + "/NewBlogEntryItem3", "data": "Third blog entry"},
        {"name": name + "/NewBlogEntryItem4", "data": "Fourth blog entry"},
    ]
    entry_meta = {CONTENTTYPE: contenttype, ITEMTYPE: ITEMTYPE_BLOG_ENTRY}

    def _publish_entry(self, entry, ptime, acl=None):
        meta = self.entry_meta.copy()
        meta[PTIME] = ptime
        if acl is not None:
            meta[ACL] = acl
        update_item(entry["name"], meta, entry["data"])

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
        data_tokens = [self.data, self.NO_ENTRIES_MSG]
        self._test_view(self.name, data_tokens=data_tokens)

    def test_do_show_entries(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # store entries without PTIME
        for entry in self.entries:
            item = Item.create(entry["name"], itemtype=ITEMTYPE_BLOG_ENTRY)
            item._save(self.entry_meta, entry["data"], comment=self.comment)
        # the blog is not empty
        exclude_data_tokens = [self.NO_ENTRIES_MSG]
        # all stored blog entries are listed on the blog index page
        data_tokens = [self.data] + [entry["data"] for entry in self.entries]
        self._test_view(self.name, data_tokens=data_tokens, exclude_data_tokens=exclude_data_tokens)

    def test_do_show_sorted_entries(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # store entries
        for entry in self.entries:
            item = Item.create(entry["name"], itemtype=ITEMTYPE_BLOG_ENTRY)
            item._save(self.entry_meta, entry["data"], comment=self.comment)
        # Add PTIME to some of the entries, ptime value is a UNIX timestamp. If PTIME
        # is not defined, we use MTIME as publication time (which is usually in the past).
        self._publish_entry(self.entries[0], ptime=2000)
        self._publish_entry(self.entries[1], ptime=1000)
        time_in_future = utctimestamp(datetime(2029, 1, 1))
        self._publish_entry(self.entries[2], ptime=time_in_future)
        # the blog is not empty
        exclude_data_tokens = [self.NO_ENTRIES_MSG]
        # blog entries are listed in reverse order relative to their PTIME/MTIMEs,
        # entries published in the future are also listed here
        ordered_data = [
            self.data,
            self.entries[2]["data"],
            self.entries[3]["data"],
            self.entries[0]["data"],
            self.entries[1]["data"],
        ]
        regex = re.compile(r"{}.*{}.*{}.*{}.*{}".format(*ordered_data), re.DOTALL)
        self._test_view(self.name, exclude_data_tokens=exclude_data_tokens, regex=regex)

    def test_filter_by_tag(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # publish some entries with tags
        entries_meta = [
            {PTIME: 1000, TAGS: ["foo", "bar", "moin"]},
            {PTIME: 3000, TAGS: ["foo", "bar", "baz"]},
            {PTIME: 2000, TAGS: ["baz", "moin"]},
        ]
        for entry, entry_meta in zip(self.entries, entries_meta):
            entry_meta.update(self.entry_meta)
            item = Item.create(entry["name"], itemtype=ITEMTYPE_BLOG_ENTRY)
            item._save(entry_meta, entry["data"], comment=self.comment)
        # filter by non-existent tag 'non-existent'
        data_tokens = [self.data, self.NO_ENTRIES_MSG]
        exclude_data_tokens = [self.entries[0]["data"], self.entries[1]["data"], self.entries[2]["data"]]
        self._test_view(
            self.name,
            req_args={"tag": "non-existent"},
            data_tokens=data_tokens,
            exclude_data_tokens=exclude_data_tokens,
        )
        # filter by tag 'moin'
        exclude_data_tokens = [self.NO_ENTRIES_MSG, self.entries[1]["data"]]
        ordered_data = [self.data, self.entries[2]["data"], self.entries[0]["data"]]
        regex = re.compile(r"{}.*{}.*{}".format(*ordered_data), re.DOTALL)
        self._test_view(self.name, req_args={"tag": "moin"}, exclude_data_tokens=exclude_data_tokens, regex=regex)

    def test_filter_by_acls(self):
        item = Item.create(self.name, itemtype=ITEMTYPE_BLOG)
        item._save(self.meta, self.data, comment=self.comment)
        # store some unpublished entries
        for entry in self.entries:
            item = Item.create(entry["name"], itemtype=ITEMTYPE_BLOG_ENTRY)
            item._save(self.entry_meta, entry["data"], comment=self.comment)
        # publish the first three entries with specific ACLs
        # we are an "anonymous" user
        self._publish_entry(self.entries[0], ptime=1000, acl="%s:read" % ANON)
        self._publish_entry(self.entries[1], ptime=3000, acl="%s:read" % ANON)
        # specify no rights on the 3rd entry
        self._publish_entry(self.entries[2], ptime=2000, acl="%s:" % ANON)
        # the blog is not empty and the 3rd entry is not displayed
        exclude_data_tokens = [self.NO_ENTRIES_MSG, self.entries[2]["data"]]
        ordered_data = [self.data, self.entries[1]["data"], self.entries[0]["data"]]
        regex = re.compile(r"{}.*{}.*{}".format(*ordered_data), re.DOTALL)
        self._test_view(self.name, exclude_data_tokens=exclude_data_tokens, regex=regex)


class TestBlogEntry(TestView):
    blog_name = "NewBlogItem"
    contenttype = "text/x.moin.wiki;charset=utf-8"
    blog_data = "This is the header item of this blog"
    blog_meta = {CONTENTTYPE: contenttype, ITEMTYPE: ITEMTYPE_BLOG}
    comment = "saved it"
    entry_name = blog_name + "/NewBlogEntryItem"
    entry_data = "Blog entry data"
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

        data_tokens = [self.blog_data, self.entry_data]
        self._test_view(self.entry_name, data_tokens=data_tokens)
