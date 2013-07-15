# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Subscriptions
"""


from flask import g as flaskg

from collections import namedtuple
from whoosh.query import Term, Or

from MoinMoin.constants.keys import (EMAIL, ITEMID, LATEST_REVS, LOCALE, NAME,
                                     NAMESPACE, SUBSCRIPTION_IDS, TAGS)


Subscriber = namedtuple('Subscriber', [ITEMID, NAME, EMAIL, LOCALE])


def get_subscribers(item):
    """ Get all users that are subscribed to the item

    :param item: Item object
    :return: a set of all item subscribers
    """
    meta = item.meta
    namespace = meta[NAMESPACE]
    terms = [Term(SUBSCRIPTION_IDS, "{0}:{1}".format(ITEMID, meta[ITEMID]))]
    terms.extend(Term(SUBSCRIPTION_IDS, "{0}:{1}:{2}".format(NAME, namespace, name))
                 for name in meta[NAME])
    terms.extend(Term(SUBSCRIPTION_IDS, "{0}:{1}:{2}".format(TAGS, namespace, tag))
                 for tag in meta[TAGS])
    query = Or(terms)
    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        results = searcher.search(query, limit=None)
        subscribers = extract_users_info(results)
    return subscribers


def extract_users_info(user_items):
    """ Extract user information (itemid, email and locale) and store it to
    Subscriber objects.

    :param user_items: whoosh.searching.Results object that contains user profile Hits
    :return: a set of users
    """
    # store just the first name
    users = {Subscriber(user[ITEMID], user[NAME][0], user[EMAIL], user[LOCALE])
             for user in user_items}
    return users
