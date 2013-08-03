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

from MoinMoin.constants.keys import (EMAIL, ITEMID, LATEST_REVS, LOCALE, NAME, NAMERE,
                                     NAMEPREFIX, NAMESPACE, SUBSCRIPTION_IDS,
                                     SUBSCRIPTION_PATTERNS, TAGS)
from MoinMoin import log
logging = log.getLogger(__name__)


Subscriber = namedtuple('Subscriber', [ITEMID, NAME, EMAIL, LOCALE])


def get_subscribers(item):
    """ Get all users that are subscribed to the item

    :param item: Item object
    :return: a set of Subscriber objects
    """
    meta = item.meta
    namespace = meta[NAMESPACE]
    terms = [Term(SUBSCRIPTION_IDS, "{0}:{1}".format(ITEMID, meta[ITEMID])), ]
    terms.extend(Term(SUBSCRIPTION_IDS, "{0}:{1}:{2}".format(NAME, namespace, name))
                 for name in meta[NAME])
    terms.extend(Term(SUBSCRIPTION_IDS, "{0}:{1}:{2}".format(TAGS, namespace, tag))
                 for tag in meta[TAGS])
    query = Or(terms)
    # TODO: check ACL behaviour - is this avoiding the protection layer?
    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        result_iterators = [searcher.search(query, limit=None), ]
        subscription_patterns = searcher.lexicon(SUBSCRIPTION_PATTERNS)
        patterns = get_matched_subscription_patterns(item, subscription_patterns)
        result_iterators.extend(searcher.documents(subscription_patterns=pattern) for pattern in patterns)
        subscribers = {Subscriber(user[ITEMID], user[NAME][0], user[EMAIL], user[LOCALE])
                       for user in chain.from_iterable(result_iterators)}
    return subscribers


def get_matched_subscription_patterns(item, subscription_patterns):
    """ Get all the subscriptions with patterns that match at least one of item names

    :param item: Item object
    :param subscription_patterns: a list of subscription patterns (the ones that
                                    start with NAMERE or NAMEPREFIX)
    :return: a list of matched subscription patterns
    """
    meta = item.meta
    item_namespace = meta[NAMESPACE]
    matched_subscriptions = []
    for subscription in subscription_patterns:
        keyword, value = subscription.split(":", 1)
        if keyword in (NAMEPREFIX, NAMERE, ):
            namespace, pattern = value.split(":", 1)
            if item_namespace == namespace:
                if keyword == NAMEPREFIX:
                    if any(name.startswith(pattern) for name in meta[NAME]):
                        matched_subscriptions.append(subscription)
                elif keyword == NAMERE:
                    try:
                        pattern = re.compile(pattern, re.U)
                    except re.error:
                        logging.error("Subscription pattern '{0}' has failed compilation.".format(pattern))
                        continue
                    if any(pattern.search(name) for name in meta[NAME]):
                        matched_subscriptions.append(subscription)
    return matched_subscriptions
