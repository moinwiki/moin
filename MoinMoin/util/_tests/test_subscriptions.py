# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.notifications Tests
"""


from flask import g as flaskg

from whoosh.query import Term

from MoinMoin import user
from MoinMoin.items import Item
from MoinMoin.constants.keys import (ITEMID, CONTENTTYPE, LATEST_REVS, NAME, TAGS)
from MoinMoin.util.subscriptions import get_subscribers, extract_users_info


class TestNotifications(object):
    reinit_storage = True

    def setup_method(self, method):
        # create an item
        self.item_name = u'foo'
        self.tagname = u'XXX'
        self.namespace = u''
        meta = {CONTENTTYPE: u'text/plain;charset=utf-8', TAGS: [self.tagname]}
        item = Item.create(self.item_name)
        item._save(meta)
        self.item = Item.create(self.item_name)

    def test_get_subscribers_empty(self):
        users = get_subscribers(self.item)
        assert users == set()
        name = u'baz'
        password = u'password'
        email = u'baz@example.org'
        meta = dict(locale=u'en')
        user.create_user(username=name, password=password, email=email, **meta)
        subscribers = get_subscribers(self.item)
        assert subscribers == set()

    def test_get_subscribers_by_itemid(self):
        name = u'bar'
        password = u'password'
        email = u'bar@example.org'
        subscriptions = ["{0}:{1}".format(ITEMID, self.item.meta[ITEMID])]
        meta = dict(locale=u'en', subscription_ids=subscriptions)
        u = user.create_user(username=name, password=password, email=email, **meta)
        u = user.User(name=name, password=password)
        subscribers = get_subscribers(self.item)
        subscribers_names = [subscriber.name for subscriber in subscribers]
        expected_name = u.profile._meta[NAME][0]
        assert expected_name in subscribers_names

    def test_get_subscribers_by_tag(self):
        name = u'barfoo'
        password = u'password'
        email = u'barfoo@examle.org'
        subscriptions = ["{0}:{1}:{2}".format(TAGS, self.namespace, self.tagname)]
        meta = dict(locale=u'en', subscription_ids=subscriptions)
        user.create_user(username=name, password=password, email=email, **meta)
        u = user.User(name=name, password=password)
        subscribers = get_subscribers(self.item)
        subscribers_names = [subscriber.name for subscriber in subscribers]
        expected_name = u.profile._meta[NAME][0]
        assert expected_name in subscribers_names

    def test_get_subscribers_by_name(self):
        name = u'foobar'
        password = u'password'
        email = u"foobar@example.org"
        subscriptions = ["{0}:{1}:{2}".format(NAME, self.namespace, self.item_name)]
        meta = dict(locale=u'en', subscription_ids=subscriptions)
        user.create_user(username=name, password=password, email=email, **meta)
        u = user.User(name=name, password=password)
        subscribers = get_subscribers(self.item)
        subscribers_names = [subscriber.name for subscriber in subscribers]
        expected_name = u.profile._meta[NAME][0]
        assert expected_name in subscribers_names

    def test_extract_users_info_empty(self):
        query = Term(u'namespace', u'userprofiles')
        with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
            results = searcher.search(query)
            users = extract_users_info(results)
            assert users == set()

    def test_extract_users_info(self):
        meta = dict(locale=u'en')
        user.create_user(username=u'foo', password=u'password',
                         email=u'foo@example.org', **meta)
        user.create_user(username=u'bar', password=u'password',
                         email=u'bar@example.org', **meta)
        u1 = user.User(name=u"foo", password=u"password")
        u2 = user.User(name=u"bar", password=u"password")
        query = Term(u'namespace', u'userprofiles')
        with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
            results = searcher.search(query)
            users = extract_users_info(results)
            users_itemids = set([u.name for u in users])
            expected_users = set([u1, u2])
            expected_users_names = set([u.name0 for u in expected_users])
            assert users_itemids == expected_users_names
