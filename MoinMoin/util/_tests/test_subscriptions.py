# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.subscriptions Tests
"""

import pytest

from MoinMoin import user
from MoinMoin.items import Item
from MoinMoin.constants.keys import (ITEMID, CONTENTTYPE, NAME, NAMERE, NAMEPREFIX,
                                     SUBSCRIPTIONS, TAGS)
from MoinMoin.constants.namespaces import NAMESPACE_DEFAULT, NAMESPACE_USERPROFILES
from MoinMoin.util.subscriptions import get_subscribers, get_matched_subscription_patterns


class TestSubscriptions(object):
    reinit_storage = True

    def setup_method(self, method):
        # create an item
        self.item_name = u'foo'
        self.tagname = u'XXX'
        self.namespace = NAMESPACE_DEFAULT
        meta = {CONTENTTYPE: u'text/plain;charset=utf-8', TAGS: [self.tagname]}
        item = Item.create(self.item_name)
        item._save(meta)
        self.item = Item.create(self.item_name)

    def test_get_subscribers(self):
        users = get_subscribers(**self.item.meta)
        assert users == set()

        name1 = u'baz'
        password = u'password'
        email1 = u'baz@example.org'
        name2 = u"bar"
        email2 = u"bar@example.org"
        name3 = u"barbaz"
        email3 = u"barbaz@example.org"
        user.create_user(username=name1, password=password, email=email1, validate=False, locale=u'en')
        user1 = user.User(name=name1, password=password)
        user.create_user(username=name2, password=password, email=email2, validate=False)
        user2 = user.User(name=name2, password=password)
        user.create_user(username=name3, password=password, email=email3, locale=u"en")
        user3 = user.User(name=name3, password=password, email1=email3)
        subscribers = get_subscribers(**self.item.meta)
        assert subscribers == set()

        namere = r'.*'
        nameprefix = u"fo"
        subscription_lists = [
            ["{0}:{1}".format(ITEMID, self.item.meta[ITEMID])],
            ["{0}:{1}:{2}".format(TAGS, self.namespace, self.tagname)],
            ["{0}:{1}:{2}".format(NAME, self.namespace, self.item_name)],
            ["{0}:{1}:{2}".format(NAMERE, self.namespace, namere)],
            ["{0}:{1}:{2}".format(NAMEPREFIX, self.namespace, nameprefix)],
        ]
        users = [user1, user2, user3]
        expected_names = {user1.name0, user2.name0}
        for subscriptions in subscription_lists:
            for user_ in users:
                user_.profile._meta[SUBSCRIPTIONS] = subscriptions
                user_.save(force=True)
            subscribers = get_subscribers(**self.item.meta)
            subscribers_names = {subscriber.name for subscriber in subscribers}
            assert subscribers_names == expected_names

    def test_get_matched_subscription_patterns(self):
        meta = self.item.meta
        patterns = get_matched_subscription_patterns([], **meta)
        assert patterns == []
        non_matching_patterns = [
            "{0}:{1}:{2}".format(NAMERE, NAMESPACE_USERPROFILES, ".*"),
            "{0}:{1}:{2}".format(NAMERE, self.namespace, "\d+"),
            "{0}:{1}:{2}".format(NAMEPREFIX, self.namespace, "bar"),
        ]
        patterns = get_matched_subscription_patterns(non_matching_patterns, **meta)
        assert patterns == []

        matching_patterns = [
            "{0}:{1}:{2}".format(NAMERE, self.namespace, "fo+"),
            "{0}:{1}:{2}".format(NAMEPREFIX, self.namespace, "fo"),
        ]
        patterns = get_matched_subscription_patterns(non_matching_patterns + matching_patterns, **meta)
        assert patterns == matching_patterns

    def test_perf_get_subscribers(self):
        pytest.skip("usually we do no performance tests")
        password = u"password"
        subscriptions = [
            "{0}:{1}".format(ITEMID, self.item.meta[ITEMID]),
            "{0}:{1}:{2}".format(NAME, self.namespace, self.item_name),
            "{0}:{1}:{2}".format(TAGS, self.namespace, self.tagname),
            "{0}:{1}:{2}".format(NAMEPREFIX, self.namespace, u"fo"),
            "{0}:{1}:{2}".format(NAMERE, self.namespace, r"\wo")
        ]
        users = set()
        expected_names = set()
        for i in xrange(10000):
            i = unicode(i)
            user.create_user(username=i, password=password, email="{0}@example.org".format(i),
                             validate=False, locale=u'en')
            user_ = user.User(name=i, password=password)
            users.add(user_)
            expected_names.add(user_.name0)

        users_sliced = list(users)[:100]
        expected_names_sliced = {user_.name0 for user_ in users_sliced}
        tests = [(users_sliced, expected_names_sliced), (users, expected_names)]

        import time
        for users_, expected_names_ in tests:
            print "\nTesting {0} subscribers from a total of {1} users".format(
                len(users_), len(users))
            for subscription in subscriptions:
                for user_ in users_:
                    user_.profile._meta[SUBSCRIPTIONS] = [subscription]
                    user_.save(force=True)
                t = time.time()
                subscribers = get_subscribers(**self.item.meta)
                elapsed_time = time.time() - t
                print "{0}: {1} s".format(subscription.split(':', 1)[0], elapsed_time)
                subscribers_names = {subscriber.name for subscriber in subscribers}
                assert subscribers_names == expected_names_
