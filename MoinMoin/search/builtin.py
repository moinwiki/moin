# Copyright: 2005 MoinMoin:FlorianFesti
# Copyright: 2005 MoinMoin:NirSoffer
# Copyright: 2005 MoinMoin:AlexanderSchremmer
# Copyright: 2006-2009 MoinMoin:ThomasWaldmann
# Copyright: 2006 MoinMoin:FranzPletz
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - search engine internals
"""


import sys, os, time, errno, codecs

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app

from flask import flaskg

from MoinMoin import wikiutil, config
from MoinMoin.util import lock, filesys
from MoinMoin.search.results import getSearchResults, Match, TextMatch, TitleMatch, getSearchResults

##############################################################################
# Search Engine Abstraction
##############################################################################


class IndexerQueue(object):
    """
    Represents a locked on-disk queue with jobs for the xapian indexer

    Each job is a tuple like: (PAGENAME, ATTACHMENTNAME, REVNO)
    PAGENAME: page name (unicode)
    ATTACHMENTNAME: attachment name (unicode) or None (for pages)
    REVNO: revision number (int) - meaning "look at that revision",
           or None - meaning "look at all revisions"
    """

    def __init__(self, request, xapian_dir, queuename, timeout=10.0):
        """
        :param request: request object
        :param xapian_dir: the xapian main directory
        :param queuename: name of the queue (used for caching key)
        :param timeout: lock acquire timeout
        """
        self.request = request
        self.xapian_dir = xapian_dir
        self.queuename = queuename
        self.timeout = timeout

    def get_cache(self, locking):
        return caching.CacheEntry(self.xapian_dir, self.queuename,
                                  scope='dir', use_pickle=True, do_locking=locking)

    def _queue(self, cache):
        try:
            queue = cache.content()
        except caching.CacheError:
            # likely nothing there yet
            queue = []
        return queue

    def put(self, pagename, attachmentname=None, revno=None):
        """ Put an entry into the queue (append at end)

        :param pagename: page name [unicode]
        :param attachmentname: attachment name [unicode]
        :param revno: revision number (int) or None (all revs)
        """
        cache = self.get_cache(locking=False) # we lock manually
        cache.lock('w', 60.0)
        try:
            queue = self._queue(cache)
            entry = (pagename, attachmentname, revno)
            queue.append(entry)
            cache.update(queue)
        finally:
            cache.unlock()

    def get(self):
        """ Get (and remove) first entry from the queue

        Raises IndexError if queue was empty when calling get().
        """
        cache = self.get_cache(locking=False) # we lock manually
        cache.lock('w', 60.0)
        try:
            queue = self._queue(cache)
            entry = queue.pop(0)
            cache.update(queue)
        finally:
            cache.unlock()
        return entry


class BaseIndex(object):
    """ Represents a search engine index """

    def __init__(self, request):
        """
        :param request: current request
        """
        self.request = request
        self.main_dir = self._main_dir()
        if not os.path.exists(self.main_dir):
            os.makedirs(self.main_dir)
        self.update_queue = IndexerQueue(request, self.main_dir, 'indexer-queue')

    def _main_dir(self):
        raise NotImplemented('...')

    def exists(self):
        """ Check if index exists """
        raise NotImplemented('...')

    def mtime(self):
        """ Modification time of the index """
        raise NotImplemented('...')

    def touch(self):
        """ Touch the index """
        raise NotImplemented('...')

    def _search(self, query):
        """ Actually perfom the search

        :param query: the search query objects tree
        """
        raise NotImplemented('...')

    def search(self, query, **kw):
        """ Search for items in the index

        :param query: the search query objects to pass to the index
        """
        return self._search(query, **kw)

    def update_item(self, pagename, attachmentname=None, revno=None, now=True):
        """ Update a single item (page or attachment) in the index

        :param pagename: the name of the page to update
        :param attachmentname: the name of the attachment to update
        :param revno: a specific revision number (int) or None (all revs)
        :param now: do all updates now (default: True)
        """
        self.update_queue.put(pagename, attachmentname, revno)
        if now:
            self.do_queued_updates()

    def indexPages(self, files=None, mode='update', pages=None):
        """ Index pages (and files, if given)

        :param files: iterator or list of files to index additionally
        :param mode: set the mode of indexing the pages, either 'update' or 'add'
        :param pages: list of pages to index, if not given, all pages are indexed
        """
        start = time.time()
        request = self._indexingRequest(self.request)
        self._index_pages(request, files, mode, pages=pages)
        logging.info("indexing completed successfully in %0.2f seconds." %
                    (time.time() - start))

    def _index_pages(self, request, files=None, mode='update', pages=None):
        """ Index all pages (and all given files)

        This should be called from indexPages only!

        :param request: current request
        :param files: iterator or list of files to index additionally
        :param mode: set the mode of indexing the pages, either 'update' or 'add'
        :param pages: list of pages to index, if not given, all pages are indexed

        """
        raise NotImplemented('...')

    def do_queued_updates(self, amount=-1):
        """ Perform updates in the queues

        :param request: the current request
        :keyword amount: how many updates to perform at once (default: -1 == all)
        """
        raise NotImplemented('...')

    def optimize(self):
        """ Optimize the index if possible """
        raise NotImplemented('...')

    def contentfilter(self, filename):
        """ Get a filter for content of filename and return unicode content.

        :param filename: name of the file
        """
        mt = wikiutil.MimeType(filename=filename)
        return mt.mime_type(), u'not implemented' # XXX see moin 1.9 code about how it was done there

    def _indexingRequest(self, request):
        """ Return a new request that can be used for index building.

        This request uses a security policy that lets the current user
        read any page. Without this policy some pages will not render,
        which will create broken pagelinks index.

        :param request: current request
        """
        import copy
        from MoinMoin.security import Permissions

        class SecurityPolicy(Permissions):

            def read(self, *args, **kw):
                return True

        r = copy.copy(request)
        r.user.may = SecurityPolicy(r.user) # XXX
        return r


##############################################################################
### Searching
##############################################################################


class BaseSearch(object):
    """ A search run """

    def __init__(self, request, query, sort='weight', mtime=None, historysearch=0):
        """
        :param request: current request
        :param query: search query objects tree
        :keyword sort: the sorting of the results (default: 'weight')
        :keyword mtime: only show items newer than this timestamp (default: None)
        :keyword historysearch: whether to show old revisions of a page (default: 0)
        """
        self.request = request
        self.query = query
        self.sort = sort
        self.mtime = mtime
        self.historysearch = historysearch
        self.filtered = False
        self.fs_rootpage = "FS" # XXX FS hardcoded

    def run(self):
        """ Perform search and return results object """

        start = time.time()
        hits, estimated_hits = self._search()

        # important - filter pages the user may not read!
        if not self.filtered:
            hits = self._filter(hits)
            logging.debug("after filtering: %d hits" % len(hits))

        return self._get_search_results(hits, start, estimated_hits)

    def _search(self):
        """
        Search pages.

        Return list of tuples (wikiname, page object, attachment,
        matches, revision) and estimated number of search results (if
        there is no estimate, None should be returned).

        The list may contain deleted pages or pages the user may not read.
        """
        raise NotImplementedError()

    def _filter(self, hits):
        """
        Filter out deleted or acl protected pages

        :param hits: list of hits
        """
        userMayRead = flaskg.user.may.read
        fs_rootpage = self.fs_rootpage + "/"
        thiswiki = (app.cfg.interwikiname, 'Self')
        filtered = [(wikiname, page, attachment, match, rev)
                for wikiname, page, attachment, match, rev in hits
                    if (not wikiname in thiswiki or
                       page.exists() and userMayRead(page.page_name) or
                       page.page_name.startswith(fs_rootpage)) and
                       (not self.mtime or self.mtime <= page.mtime_usecs()/1000000)]
        return filtered

    def _get_search_results(self, hits, start, estimated_hits):
        return getSearchResults(self.request, self.query, hits, start, self.sort, estimated_hits)

    def _get_match(self, page=None, uid=None):
        """
        Get all matches

        :param page: the current page instance
        """
        if page:
            return self.query.search(page)

    def _getHits(self, pages):
        """ Get the hit tuples in pages through _get_match """
        logging.debug("_getHits searching in %d pages ..." % len(pages))
        from MoinMoin.Page import Page
        hits = []
        revisionCache = {}
        fs_rootpage = self.fs_rootpage
        for hit in pages:

            uid = hit.get('uid')
            wikiname = hit['wikiname']
            pagename = hit['pagename']
            attachment = hit['attachment']
            revision = int(hit.get('revision', 0))

            logging.debug("_getHits processing %r %r %d %r" % (wikiname, pagename, revision, attachment))

            if wikiname in (app.cfg.interwikiname, 'Self'): # THIS wiki
                page = Page(self.request, pagename, rev=revision)

                if not self.historysearch and revision:
                    revlist = page.getRevList()
                    # revlist can be empty if page was nuked/renamed since it was included in xapian index
                    if not revlist or revlist[0] != revision:
                        # nothing there at all or not the current revision
                        logging.debug("no history search, skipping non-current revision...")
                        continue

                if attachment:
                    # revision currently is 0 ever
                    if pagename == fs_rootpage: # not really an attachment
                        page = Page(self.request, "%s/%s" % (fs_rootpage, attachment))
                        hits.append((wikiname, page, None, None, revision))
                    else:
                        matches = self._get_match(page=None, uid=uid)
                        hits.append((wikiname, page, attachment, matches, revision))
                else:
                    matches = self._get_match(page=page, uid=uid)
                    logging.debug("self._get_match %r" % matches)
                    if matches:
                        if not self.historysearch and pagename in revisionCache and revisionCache[pagename][0] < revision:
                            hits.remove(revisionCache[pagename][1])
                            del revisionCache[pagename]
                        hits.append((wikiname, page, attachment, matches, revision))
                        revisionCache[pagename] = (revision, hits[-1])

            else: # other wiki
                hits.append((wikiname, pagename, attachment, None, revision))
        logging.debug("_getHits returning %r." % hits)
        return hits


class MoinSearch(BaseSearch):

    def __init__(self, request, query, sort='weight', mtime=None, historysearch=0, pages=None):
        super(MoinSearch, self).__init__(request, query, sort, mtime, historysearch)

        self.pages = pages

    def _search(self):
        """
        Search pages using moin's built-in full text search

        The list may contain deleted pages or pages the user may not
        read.

        if self.pages is not None, searches in that pages.
        """
        # if self.pages is none, we make a full pagelist, but don't
        # search attachments (thus attachment name = '')
        pages = self.pages or [{'pagename': p, 'attachment': '', 'wikiname': 'Self', } for p in self._getPageList()]

        hits = self._getHits(pages)
        return hits, None

    def _getPageList(self):
        """ Get list of pages to search in

        If the query has a page filter, use it to filter pages before
        searching. If not, get a unfiltered page list. The filtering
        will happen later on the hits, which is faster with current
        slow storage.
        """
        filter_ = self.query.pageFilter()
        if filter_:
            # There is no need to filter the results again.
            self.filtered = True
            return self.request.rootpage.getPageList(filter=filter_)
        else:
            return self.request.rootpage.getPageList(user='')

