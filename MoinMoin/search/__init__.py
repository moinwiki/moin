# Copyright: 2005 MoinMoin:FlorianFesti
# Copyright: 2005 MoinMoin:NirSoffer
# Copyright: 2005 MoinMoin:AlexanderSchremmer
# Copyright: 2006 MoinMoin:ThomasWaldmann
# Copyright: 2006 MoinMoin:FranzPletz
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - search engine
"""


from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app

from MoinMoin.search.queryparser import QueryParser, QueryError
from MoinMoin.search.builtin import MoinSearch


def searchPages(request, query, sort='weight', mtime=None, historysearch=None, **kw):
    """
    Search the text of all pages for query.

    :param request: current request
    :param query: the expression (string or query objects) we want to search for
    :keyword sort: sorting of the search results, either 'weight' or 'page_name'
    :keyword mtime: only items modified since mtime
    :keyword historysearch: include older revisions of items in search
    :keyword titlesearch: treat all terms as title searches (passed to qp)
    :keyword case: do case sensitive search (passed to qp)
    :keyword regex: treat all terms as regular expression (passed to qp)
    :rtype: SearchResults instance
    :returns: search results
    """
    return _get_searcher(request, query, sort, mtime, historysearch, **kw).run()


def _get_searcher(request, query, sort='weight', mtime=None, historysearch=None, **kw):
    """
    Return a searcher object according to the configuration.
    """
    query = _parse_query(query, **kw)
    searcher = None

    if app.cfg.xapian_search:
        try:
            from MoinMoin.search.Xapian.search import XapianSearch, IndexDoesNotExistError
            searcher = XapianSearch(request, query, sort, mtime=mtime, historysearch=historysearch)
        except ImportError, error:
            logging.warning("%s. You should either set xapian_search = False in your wiki config or install/upgrade Xapian." % str(error))
        except IndexDoesNotExistError:
            logging.warning("Slow moin search is used because the Xapian index does not exist. You should create it using the moin index build command.")

    if searcher is None:
        searcher = MoinSearch(request, query, sort, mtime=mtime, historysearch=historysearch)

    return searcher

def _parse_query(query, **kw):
    if isinstance(query, str) or isinstance(query, unicode):
        query = QueryParser(**kw).parse_query(query)

    return query

