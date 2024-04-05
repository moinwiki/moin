# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.utils.subscriptions Tests
"""

import pytest

from moin import user
from moin.items import Item
from moin.constants.keys import ACL, ITEMID, CONTENTTYPE, NAME, NAMERE, NAMEPREFIX, SUBSCRIPTIONS, TAGS
from moin.constants.namespaces import NAMESPACE_DEFAULT, NAMESPACE_USERPROFILES
from moin.utils.subscriptions import get_subscribers, get_matched_subscription_patterns


class TestSubscriptions:
    reinit_storage = True

    @pytest.fixture
    def item_name(self):
        return "foo"

    @pytest.fixture
    def tag_name(self):
        return "XXX"

    @pytest.fixture
    def namespace(self):
        return NAMESPACE_DEFAULT

    @pytest.fixture
    def meta(self, tag_name):
        return {CONTENTTYPE: "text/plain;charset=utf-8", TAGS: [tag_name]}

    @pytest.fixture
    def item(self, item_name, meta):
        item = Item.create(item_name)
        item._save(meta)
        return Item.create(item_name)

    def test_get_subscribers(self, item, item_name, namespace, tag_name):
        users = get_subscribers(**item.meta)
        assert users == set()

        name1 = "baz"
        password = "password"
        email1 = "baz@example.org"
        name2 = "bar"
        email2 = "bar@example.org"
        name3 = "barbaz"
        email3 = "barbaz@example.org"
        user.create_user(username=name1, password=password, email=email1, validate=False, locale="en")
        user1 = user.User(name=name1, password=password)
        user.create_user(username=name2, password=password, email=email2, validate=False)
        user2 = user.User(name=name2, password=password)
        user.create_user(username=name3, password=password, email=email3, verify_email=True, locale="en")
        user3 = user.User(name=name3, password=password, email=email3)
        subscribers = get_subscribers(**item.meta)
        assert subscribers == set()

        namere = r".*"
        nameprefix = "fo"
        subscription_lists = [
            [f"{ITEMID}:{item.meta[ITEMID]}"],
            [f"{TAGS}:{namespace}:{tag_name}"],
            [f"{NAME}:{namespace}:{item_name}"],
            [f"{NAMERE}:{namespace}:{namere}"],
            [f"{NAMEPREFIX}:{namespace}:{nameprefix}"],
        ]
        users = [user1, user2, user3]
        expected_names = {user1.name0, user2.name0}
        for subscriptions in subscription_lists:
            for user_ in users:
                user_.profile._meta[SUBSCRIPTIONS] = subscriptions
                user_.save(force=True)
            subscribers = get_subscribers(**item.meta)
            subscribers_names = {subscriber.name for subscriber in subscribers}
            assert subscribers_names == expected_names

        meta = {CONTENTTYPE: "text/plain;charset=utf-8", ACL: f"{user1.name0}: All:read,write"}
        item._save(meta, comment="")
        item = Item.create(item_name)
        subscribers = get_subscribers(**item.meta)
        assert {subscriber.name for subscriber in subscribers} == {user2.name0}

    def test_get_matched_subscription_patterns(self, item, namespace):
        meta = item.meta
        patterns = get_matched_subscription_patterns([], **meta)
        assert patterns == []
        non_matching_patterns = [
            "{}:{}:{}".format(NAMERE, NAMESPACE_USERPROFILES, r".*"),
            "{}:{}:{}".format(NAMERE, namespace, r"\d+"),
            "{}:{}:{}".format(NAMEPREFIX, namespace, r"bar"),
        ]
        patterns = get_matched_subscription_patterns(non_matching_patterns, **meta)
        assert patterns == []

        matching_patterns = [
            "{}:{}:{}".format(NAMERE, namespace, r"fo+"),
            "{}:{}:{}".format(NAMEPREFIX, namespace, r"fo"),
        ]
        patterns = get_matched_subscription_patterns(non_matching_patterns + matching_patterns, **meta)
        assert patterns == matching_patterns

    def test_perf_get_subscribers(self):
        pytest.skip("usually we do no performance tests")
        password = "password"
        subscriptions = [
            f"{ITEMID}:{self.item.meta[ITEMID]}",
            f"{NAME}:{self.namespace}:{self.item_name}",
            f"{TAGS}:{self.namespace}:{self.tagname}",
            "{}:{}:{}".format(NAMEPREFIX, self.namespace, "fo"),
            "{}:{}:{}".format(NAMERE, self.namespace, r"\wo"),
        ]
        users = set()
        expected_names = set()
        for i in range(10000):
            i = str(i)
            user.create_user(username=i, password=password, email=f"{i}@example.org", validate=False, locale="en")
            user_ = user.User(name=i, password=password)
            users.add(user_)
            expected_names.add(user_.name0)

        users_sliced = list(users)[:100]
        expected_names_sliced = {user_.name0 for user_ in users_sliced}
        tests = [(users_sliced, expected_names_sliced), (users, expected_names)]

        import time

        for users_, expected_names_ in tests:
            print("\nTesting {} subscribers from a total of {} users".format(len(users_), len(users)))
            for subscription in subscriptions:
                for user_ in users_:
                    user_.profile._meta[SUBSCRIPTIONS] = [subscription]
                    user_.save(force=True)
                t = time.time()
                subscribers = get_subscribers(**self.item.meta)
                elapsed_time = time.time() - t
                print("{}: {} s".format(subscription.split(":", 1)[0], elapsed_time))
                subscribers_names = {subscriber.name for subscriber in subscribers}
                assert subscribers_names == expected_names_
