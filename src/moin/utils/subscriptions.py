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

from moin.constants.keys import (
    DEFAULT_LOCALE,
    EMAIL,
    ITEMID,
    LATEST_REVS,
    LOCALE,
    NAME,
    NAMERE,
    NAMEPREFIX,
    NAMESPACE,
    SUBSCRIPTION_IDS,
    SUBSCRIPTION_PATTERNS,
    TAGS,
)

from moin.utils.interwiki import CompositeName

from moin import log

logging = log.getLogger(__name__)


Subscriber = namedtuple("Subscriber", [ITEMID, NAME, EMAIL, LOCALE])


def get_subscribers(**meta):
    """Get all users that are subscribed to the item

    :param meta: key/value pairs from item metadata - itemid, name, namespace, tags keys
    :return: a set of Subscriber objects
    """
    itemid = meta.get(ITEMID)
    name = meta.get(NAME)
    namespace = meta.get(NAMESPACE)
    fqname = CompositeName(namespace, ITEMID, itemid)
    tags = meta.get(TAGS)
    terms = []
    if itemid is not None:
        terms.extend([Term(SUBSCRIPTION_IDS, f"{ITEMID}:{itemid}")])
    if namespace is not None:
        if name is not None:
            terms.extend(Term(SUBSCRIPTION_IDS, f"{NAME}:{namespace}:{name_}") for name_ in name)
        if tags is not None:
            terms.extend(Term(SUBSCRIPTION_IDS, f"{TAGS}:{namespace}:{tag}") for tag in tags)
    query = Or(terms)
    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        result_iterators = [searcher.search(query, limit=None)]
        subscription_patterns = searcher.lexicon(SUBSCRIPTION_PATTERNS)
        # looks like whoosh gives us bytes (not str), decode them:
        subscription_patterns = [p if isinstance(p, str) else p.decode() for p in subscription_patterns]
        patterns = get_matched_subscription_patterns(subscription_patterns, **meta)
        result_iterators.extend(searcher.documents(subscription_patterns=pattern) for pattern in patterns)
        subscribers = set()
        for user in chain.from_iterable(result_iterators):
            email = user.get(EMAIL)
            if email:
                from moin.user import User

                u = User(uid=user.get(ITEMID))
                if u.may.read(fqname):
                    locale = user.get(LOCALE, DEFAULT_LOCALE)
                    subscribers.add(Subscriber(user[ITEMID], user[NAME][0], email, locale))
    return subscribers


def get_matched_subscription_patterns(subscription_patterns, **meta):
    """Get all the subscriptions with patterns that match at least one of item names

    :param subscription_patterns: a list of subscription patterns (the ones that
                                    start with NAMERE or NAMEPREFIX)
    :param meta: key/value pairs from item metadata - name and namespace keys
    :return: a list of matched subscription patterns
    """
    item_names = meta.get(NAME)
    item_namespace = meta.get(NAMESPACE)
    matched_subscriptions = []
    for subscription in subscription_patterns:
        try:
            keyword, value = subscription.split(":", 1)
        except ValueError:
            logging.exception(f"User {flaskg.user.name[0]} has invalid subscription entry: {subscription}")
            continue
        if keyword in (NAMEPREFIX, NAMERE) and item_namespace is not None and item_names:
            try:
                namespace, pattern = value.split(":", 1)
            except ValueError:
                logging.exception(f"User {flaskg.user.name[0]} has invalid subscription entry: {subscription}")
                continue
            if item_namespace == namespace:
                if keyword == NAMEPREFIX:
                    if any(name.startswith(pattern) for name in item_names):
                        matched_subscriptions.append(subscription)
                elif keyword == NAMERE:
                    try:
                        pattern = re.compile(pattern, re.U)
                    except re.error:
                        logging.error(f"Subscription pattern '{pattern}' has failed compilation.")
                        continue
                    if any(pattern.search(name) for name in item_names):
                        matched_subscriptions.append(subscription)
    return matched_subscriptions
