# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Subscriptions
"""

import re
from collections import namedtuple
from itertools import chain

from flask import g as flaskg

from whoosh.query import Term, Or

from MoinMoin.constants.keys import (DEFAULT_LOCALE, EMAIL, EMAIL_UNVALIDATED, ITEMID,
                                     LATEST_REVS, LOCALE, NAME, NAMERE, NAMEPREFIX,
                                     NAMESPACE, SUBSCRIPTION_IDS, SUBSCRIPTION_PATTERNS, TAGS)
from MoinMoin import log
logging = log.getLogger(__name__)


Subscriber = namedtuple('Subscriber', [ITEMID, NAME, EMAIL, LOCALE])


def get_subscribers(**meta):
    """ Get all users that are subscribed to the item

    :param meta: key/value pairs from item metadata - itemid, name, namespace, tags keys
    :return: a set of Subscriber objects
    """
    itemid = meta.get(ITEMID)
    name = meta.get(NAME)
    namespace = meta.get(NAMESPACE)
    tags = meta.get(TAGS)
    terms = []
    if itemid is not None:
        terms.extend([Term(SUBSCRIPTION_IDS, "{0}:{1}".format(ITEMID, itemid))])
    if namespace is not None:
        if name is not None:
            terms.extend(Term(SUBSCRIPTION_IDS, "{0}:{1}:{2}".format(NAME, namespace, name_))
                         for name_ in name)
        if tags is not None:
            terms.extend(Term(SUBSCRIPTION_IDS, "{0}:{1}:{2}".format(TAGS, namespace, tag))
                         for tag in tags)
    query = Or(terms)
    # TODO: check ACL behaviour - is this avoiding the protection layer?
    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        result_iterators = [searcher.search(query, limit=None), ]
        subscription_patterns = searcher.lexicon(SUBSCRIPTION_PATTERNS)
        patterns = get_matched_subscription_patterns(subscription_patterns, **meta)
        result_iterators.extend(searcher.documents(subscription_patterns=pattern) for pattern in patterns)
        subscribers = set()
        for user in chain.from_iterable(result_iterators):
            email = user.get(EMAIL)
            if email:
                locale = user.get(LOCALE, DEFAULT_LOCALE)
                subscribers.add(Subscriber(user[ITEMID], user[NAME][0], email, locale))
    return subscribers


def get_matched_subscription_patterns(subscription_patterns, **meta):
    """ Get all the subscriptions with patterns that match at least one of item names

    :param subscription_patterns: a list of subscription patterns (the ones that
                                    start with NAMERE or NAMEPREFIX)
    :param meta: key/value pairs from item metadata - name and namespace keys
    :return: a list of matched subscription patterns
    """
    item_names = meta.get(NAME)
    item_namespace = meta.get(NAMESPACE)
    matched_subscriptions = []
    for subscription in subscription_patterns:
        keyword, value = subscription.split(":", 1)
        if keyword in (NAMEPREFIX, NAMERE, ) and item_namespace is not None and item_names:
            namespace, pattern = value.split(":", 1)
            if item_namespace == namespace:
                if keyword == NAMEPREFIX:
                    if any(name.startswith(pattern) for name in item_names):
                        matched_subscriptions.append(subscription)
                elif keyword == NAMERE:
                    try:
                        pattern = re.compile(pattern, re.U)
                    except re.error:
                        logging.error("Subscription pattern '{0}' has failed compilation.".format(pattern))
                        continue
                    if any(pattern.search(name) for name in item_names):
                        matched_subscriptions.append(subscription)
    return matched_subscriptions
