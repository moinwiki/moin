# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - search engine internals

    @copyright: 2005 MoinMoin:FlorianFesti,
                2005 MoinMoin:NirSoffer,
                2005 MoinMoin:AlexanderSchremmer,
                2006-2009 MoinMoin:ThomasWaldmann,
                2006 MoinMoin:FranzPletz
    @license: GNU GPL, see COPYING for details
"""


from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.i18n import _, L_, N_
from MoinMoin.search.builtin import BaseSearch, MoinSearch, BaseIndex
from MoinMoin.search.Xapian.indexing import XapianIndex

class IndexDoesNotExistError(Exception):
    pass

class XapianSearch(BaseSearch):

    def __init__(self, request, query, sort='weight', mtime=None, historysearch=0):
        super(XapianSearch, self).__init__(request, query, sort, mtime, historysearch)

        self.index = self._xapian_index()

    def _xapian_index(self):
        """ Get the xapian index if possible

        @param request: current request
        """
        index = XapianIndex(self.request)

        if not index.exists():
            raise IndexDoesNotExistError

        return index

    def _search(self):
        """ Search using Xapian

        Get a list of pages using fast xapian search and
        return moin search in those pages if needed.
        """
        index = self.index

        search_results = index.search(self.query, sort=self.sort, historysearch=self.historysearch)
        logging.debug("_xapianSearch: finds: %r" % search_results)

        # Note: .data is (un)pickled inside xappy, so we get back exactly what
        #       we had put into it at indexing time (including unicode objects).
        pages = [{'uid': r.id,
                  'wikiname': r.data['wikiname'][0],
                  'pagename': r.data['pagename'][0],
                  'attachment': r.data['attachment'][0],
                  'revision': r.data.get('revision', [0])[0]}
                 for r in search_results]
        if not self.query.xapian_need_postproc():
            # xapian handled the full query

            return self._getHits(pages), (search_results.estimate_is_exact and '' or _('about'), search_results.matches_estimated)

        # some postprocessing by MoinSearch is required
        return MoinSearch(self.request, self.query, self.sort, self.mtime, self.historysearch, pages=pages)._search()


