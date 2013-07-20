# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.subscriptions Tests
"""


from MoinMoin import user
from MoinMoin.items import Item
from MoinMoin.constants.keys import (ITEMID, CONTENTTYPE, NAME, NAMERE, NAMEPREFIX,
                                     SUBSCRIPTIONS, TAGS)
from MoinMoin.util.subscriptions import get_subscribers, get_matched_subscription_patterns


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

    def test_get_subscribers(self):
        users = get_subscribers(self.item)
        assert users == set()

        name = u'baz'
        password = u'password'
        email = u'baz@example.org'
        user.create_user(username=name, password=password, email=email, validate=False, locale=u'en')
        user_ = user.User(name=name, password=password)
        subscribers = get_subscribers(self.item)
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
        expected_name = user_.name0
        for subscriptions in subscription_lists:
            user_.profile._meta[SUBSCRIPTIONS] = subscriptions
            user_.save(force=True)
            subscribers = get_subscribers(self.item)
            subscribers_names = [subscriber.name for subscriber in subscribers]
            assert subscribers_names == [expected_name]

    def test_get_matched_subscription_patterns(self):
        patterns = get_matched_subscription_patterns(self.item, [])
        assert patterns == []
        non_matching_patterns = [
            "{0}:{1}:{2}".format(NAMERE, "userprofile", ".*"),
            "{0}:{1}:{2}".format(NAMERE, self.namespace, "\d+"),
            "{0}:{1}:{2}".format(NAMEPREFIX, self.namespace, "bar"),
        ]
        patterns = get_matched_subscription_patterns(self.item, non_matching_patterns)
        assert patterns == []

        matching_patterns = [
            "{0}:{1}:{2}".format(NAMERE, self.namespace, "fo+"),
            "{0}:{1}:{2}".format(NAMEPREFIX, self.namespace, "fo"),
        ]
        patterns = get_matched_subscription_patterns(self.item,
                                                     non_matching_patterns + matching_patterns)
        assert patterns == matching_patterns
