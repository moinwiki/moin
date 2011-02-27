# Copyright: 2006-2009 MoinMoin:ThomasWaldmann
# Copyright: 2006 MoinMoin:FranzPletz
# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - xapian search engine indexing
"""


import os, re
import xapian
import xappy

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app

from MoinMoin.search.builtin import BaseIndex
from MoinMoin.search.Xapian.tokenizer import WikiAnalyzer
from MoinMoin.util import filesys

from MoinMoin.Page import Page
from MoinMoin import config, wikiutil


class Query(xapian.Query):
    pass


class UnicodeQuery(xapian.Query):
    """ Xapian query object which automatically encodes unicode strings """

    def __init__(self, *args, **kwargs):
        """
        @keyword encoding: specify the encoding manually (default: value of config.charset)
        """
        self.encoding = kwargs.get('encoding', config.charset)

        nargs = []
        for term in args:
            if isinstance(term, unicode):
                term = term.encode(self.encoding)
            elif isinstance(term, list) or isinstance(term, tuple):
                term = [t.encode(self.encoding) for t in term]
            nargs.append(term)

        Query.__init__(self, *nargs, **kwargs)


class MoinSearchConnection(xappy.SearchConnection):

    def get_all_documents(self, query=None):
        """
        Return all the documents in the index (that match query, if given).
        """
        document_count = self.get_doccount()
        query = query or self.query_all()
        hits = self.search(query, 0, document_count)
        return hits

    def get_all_documents_with_fields(self, **fields):
        """
        Return all the documents in the index (that match the field=value kwargs given).
        """
        field_queries = [self.query_field(field, value) for field, value in fields.iteritems()]
        query = self.query_composite(self.OP_AND, field_queries)
        return self.get_all_documents(query)


XapianDatabaseLockError = xappy.XapianDatabaseLockError

class MoinIndexerConnection(xappy.IndexerConnection):

    def __init__(self, *args, **kwargs):
        super(MoinIndexerConnection, self).__init__(*args, **kwargs)
        self._define_fields_actions()

    def _define_fields_actions(self):
        SORTABLE = xappy.FieldActions.SORTABLE
        INDEX_EXACT = xappy.FieldActions.INDEX_EXACT
        INDEX_FREETEXT = xappy.FieldActions.INDEX_FREETEXT
        STORE_CONTENT = xappy.FieldActions.STORE_CONTENT

        self.add_field_action('wikiname', INDEX_EXACT)
        self.add_field_action('wikiname', STORE_CONTENT)
        self.add_field_action('pagename', INDEX_EXACT)
        self.add_field_action('pagename', STORE_CONTENT)
        self.add_field_action('pagename', SORTABLE)
        self.add_field_action('attachment', INDEX_EXACT)
        self.add_field_action('attachment', STORE_CONTENT)
        self.add_field_action('mtime', INDEX_EXACT)
        self.add_field_action('mtime', STORE_CONTENT)
        self.add_field_action('revision', STORE_CONTENT)
        self.add_field_action('revision', INDEX_EXACT)
        self.add_field_action('mimetype', INDEX_EXACT)
        self.add_field_action('mimetype', STORE_CONTENT)
        self.add_field_action('title', INDEX_FREETEXT, weight=100)
        self.add_field_action('title', STORE_CONTENT)
        self.add_field_action('content', INDEX_FREETEXT, spell=True)
        self.add_field_action('domain', INDEX_EXACT)
        self.add_field_action('domain', STORE_CONTENT)
        self.add_field_action('lang', INDEX_EXACT)
        self.add_field_action('lang', STORE_CONTENT)
        self.add_field_action('stem_lang', INDEX_EXACT)
        self.add_field_action('author', INDEX_EXACT)
        self.add_field_action('linkto', INDEX_EXACT)
        self.add_field_action('linkto', STORE_CONTENT)


class StemmedField(xappy.Field):

    def __init__(self, name, value, request):
        analyzer = WikiAnalyzer(language=app.cfg.language_default)
        value = ' '.join(unicode('%s %s' % (word, stemmed)).strip() for word, stemmed in analyzer.tokenize(value))
        super(StemmedField, self).__init__(name, value)


class XapianIndex(BaseIndex):

    def __init__(self, request, name='index'):
        super(XapianIndex, self).__init__(request)
        self.db = os.path.join(self.main_dir, name)

    def _main_dir(self):
        """ Get the directory of the xapian index """
        return os.path.join(app.cfg.xapian_index_dir, app.cfg.siteid)

    def exists(self):
        """ Check if index exists """
        return os.path.exists(self.db)

    def mtime(self):
        """ Modification time of the index """
        return os.path.getmtime(self.db)

    def touch(self):
        """ Touch the index """
        filesys.touch(self.db)

    def get_search_connection(self):
        return MoinSearchConnection(self.db)

    def get_indexer_connection(self):
        return MoinIndexerConnection(self.db)

    def _search(self, query, sort='weight', historysearch=0):
        """
        Perform the search using xapian

        @param query: the search query objects
        @param sort: the sorting of the results (default: 'weight')
        @param historysearch: whether to search in all page revisions (default: 0) TODO: use/implement this
        """
        while True:
            try:
                searcher, timestamp = app.cfg.xapian_searchers.pop()
                if timestamp != self.mtime():
                    searcher.close()
                else:
                    break
            except IndexError:
                searcher = self.get_search_connection()
                timestamp = self.mtime()
                break

        # Refresh connection, since it may be outdated.
        searcher.reopen()
        query = query.xapian_term(self.request, searcher)

        # Get maximum possible amount of hits from xappy, which is number of documents in the index.
        document_count = searcher.get_doccount()

        kw = {}
        if sort == 'page_name':
            kw['sortby'] = 'pagename'

        hits = searcher.search(query, 0, document_count, **kw)

        app.cfg.xapian_searchers.append((searcher, timestamp))
        return hits

    def do_queued_updates(self, amount=-1):
        """ Index <amount> entries from the indexer queue.

            @param amount: amount of queue entries to process (default: -1 == all)
        """
        try:
            request = self._indexingRequest(self.request)
            connection = self.get_indexer_connection()
            self.touch()
            try:
                done_count = 0
                while amount:
                    # trick: if amount starts from -1, it will never get 0
                    amount -= 1
                    try:
                        pagename, attachmentname, revno = self.update_queue.get()
                    except IndexError:
                        # queue empty
                        break
                    else:
                        logging.debug("got from indexer queue: %r %r %r" % (pagename, attachmentname, revno))
                        if not attachmentname:
                            if revno is None:
                                # generic "index this page completely, with attachments" request
                                self._index_page(request, connection, pagename, mode='update')
                            else:
                                # "index this page revision" request
                                self._index_page_rev(request, connection, pagename, revno, mode='update')
                        else:
                            # "index this attachment" request
                            self._index_attachment(request, connection, pagename, attachmentname, mode='update')
                        done_count += 1
            finally:
                logging.debug("updated xapian index with %d queued updates" % done_count)
                connection.close()
        except XapianDatabaseLockError:
            # another indexer has locked the index, we can retry it later...
            logging.debug("can't lock xapian index, not doing queued updates now")

    def _get_document(self, connection, doc_id, mtime, mode):
        do_index = False

        if mode == 'update':
            try:
                doc = connection.get_document(doc_id)
                docmtime = long(doc.data['mtime'][0])
            except KeyError:
                do_index = True
            else:
                do_index = mtime > docmtime
        elif mode == 'add':
            do_index = True
        else:
            raise ValueError("mode must be 'update' or 'add'")

        if do_index:
            document = xappy.UnprocessedDocument()
            document.id = doc_id
        else:
            document = None
        return document

    def _add_fields_to_document(self, request, document, fields=None, multivalued_fields=None):

        fields_to_stem = ['title', 'content']

        if fields is None:
            fields = {}
        if multivalued_fields is None:
            multivalued_fields = {}

        for field, value in fields.iteritems():
            document.fields.append(xappy.Field(field, value))
            if field in fields_to_stem:
                document.fields.append(StemmedField(field, value, request))

        for field, values in multivalued_fields.iteritems():
            for value in values:
                document.fields.append(xappy.Field(field, value))

    def _get_languages(self, page):
        """ Get language of a page and the language to stem it in

        @param page: the page instance
        """
        lang = None
        default_lang = app.cfg.language_default

        # if we should stem, we check if we have a stemmer for the language available
        if app.cfg.xapian_stemming:
            lang = page.pi['language']
            try:
                xapian.Stem(lang)
                # if there is no exception, lang is stemmable
                return (lang, lang)
            except xapian.InvalidArgumentError:
                # lang is not stemmable
                pass

        if not lang:
            # no lang found at all.. fallback to default language
            lang = default_lang

        # return actual lang and lang to stem in
        return (lang, default_lang)

    def _get_domains(self, page):
        """ Returns a generator with all the domains the page belongs to

        @param page: page
        """
        if page.isStandardPage():
            yield 'standard'
        if wikiutil.isSystemItem(page.page_name):
            yield 'system'

    def _index_page(self, request, connection, pagename, mode='update'):
        """ Index a page.

        Index all revisions (if wanted by configuration) and all attachments.

        @param request: request suitable for indexing
        @param connection: the Indexer connection object
        @param pagename: a page name
        @param mode: 'add' = just add, no checks
                     'update' = check if already in index and update if needed (mtime)
        """
        page = Page(request, pagename)
        revlist = page.getRevList() # recent revs first, does not include deleted revs
        logging.debug("indexing page %r, %d revs found" % (pagename, len(revlist)))

        if not revlist:
            # we have an empty revision list, that means the page is not there any more,
            # likely it (== all of its revisions, all of its attachments) got either renamed or nuked
            wikiname = app.cfg.interwikiname or u'Self'

            sc = self.get_search_connection()
            docs_to_delete = sc.get_all_documents_with_fields(wikiname=wikiname, pagename=pagename)
                                                              # any page rev, any attachment
            sc.close()

            for doc in docs_to_delete:
                connection.delete(doc.id)
            logging.debug('page %s (all revs, all attachments) removed from xapian index' % pagename)

        else:
            if app.cfg.xapian_index_history:
                index_revs, remove_revs = revlist, []
            else:
                if page.exists(): # is current rev not deleted?
                    index_revs, remove_revs = revlist[:1], revlist[1:]
                else:
                    index_revs, remove_revs = [], revlist

            for revno in index_revs:
                updated = self._index_page_rev(request, connection, pagename, revno, mode=mode)
                logging.debug("updated page %r rev %d (updated==%r)" % (pagename, revno, updated))
                if not updated:
                    # we reached the revisions that are already present in the index
                    break

            for revno in remove_revs:
                # XXX remove_revs can be rather long for pages with many revs and
                # XXX most page revs usually will be already deleted. optimize?
                self._remove_page_rev(request, connection, pagename, revno)
                logging.debug("removed page %r rev %d" % (pagename, revno))

            from MoinMoin.action import AttachFile
            for attachmentname in AttachFile._get_files(request, pagename):
                self._index_attachment(request, connection, pagename, attachmentname, mode)

    def _index_page_rev(self, request, connection, pagename, revno, mode='update'):
        """ Index a page revision.

        @param request: request suitable for indexing
        @param connection: the Indexer connection object
        @param pagename: the page name
        @param revno: page revision number (int)
        @param mode: 'add' = just add, no checks
                     'update' = check if already in index and update if needed (mtime)
        """
        page = Page(request, pagename, rev=revno)

        wikiname = app.cfg.interwikiname or u"Self"
        revision = str(page.get_real_rev())
        itemid = "%s:%s:%s" % (wikiname, pagename, revision)
        #mtime = wikiutil.timestamp2version(page.mtime())
        mtime = page.mtime_usecs()

        doc = self._get_document(connection, itemid, mtime, mode)
        logging.debug("%s %s %r" % (pagename, revision, doc))
        if doc:
            mimetype = 'text/%s' % page.pi['format']  # XXX improve this

            fields = {}
            fields['wikiname'] = wikiname
            fields['pagename'] = pagename
            fields['attachment'] = '' # this is a real page, not an attachment
            fields['mtime'] = str(mtime)
            fields['revision'] = revision
            fields['title'] = pagename
            fields['content'] = page.get_raw_body()
            fields['lang'], fields['stem_lang'] = self._get_languages(page)
            fields['author'] = page.edit_info().get('editor', '?')

            multivalued_fields = {}
            multivalued_fields['mimetype'] = [mt for mt in [mimetype] + mimetype.split('/')]
            multivalued_fields['domain'] = self._get_domains(page)
            multivalued_fields['linkto'] = page.getPageLinks(request)

            self._add_fields_to_document(request, doc, fields, multivalued_fields)

            try:
                connection.replace(doc)
            except xappy.IndexerError, err:
                logging.warning("IndexerError at %r %r %r (%s)" % (
                    wikiname, pagename, revision, str(err)))

        return bool(doc)

    def _remove_page_rev(self, request, connection, pagename, revno):
        """ Remove a page revision from the index.

        @param request: request suitable for indexing
        @param connection: the Indexer connection object
        @param pagename: the page name
        @param revno: a real revision number (int), > 0
        """
        wikiname = app.cfg.interwikiname or u"Self"
        revision = str(revno)
        itemid = "%s:%s:%s" % (wikiname, pagename, revision)
        connection.delete(itemid)
        logging.debug('page %s, revision %d removed from index' % (pagename, revno))

    def _index_attachment(self, request, connection, pagename, attachmentname, mode='update'):
        """ Index an attachment

        @param request: request suitable for indexing
        @param connection: the Indexer connection object
        @param pagename: the page name
        @param attachmentname: the attachment's name
        @param mode: 'add' = just add, no checks
                     'update' = check if already in index and update if needed (mtime)
        """
        from MoinMoin.action import AttachFile
        wikiname = app.cfg.interwikiname or u"Self"
        itemid = "%s:%s//%s" % (wikiname, pagename, attachmentname)

        filename = AttachFile.getFilename(request, pagename, attachmentname)
        # check if the file is still there. as we might be doing queued index updates,
        # the file could be gone meanwhile...
        if os.path.exists(filename):
            mtime = wikiutil.timestamp2version(os.path.getmtime(filename))
            doc = self._get_document(connection, itemid, mtime, mode)
            logging.debug("%s %s %r" % (pagename, attachmentname, doc))
            if doc:
                page = Page(request, pagename)
                mimetype, att_content = self.contentfilter(filename)

                fields = {}
                fields['wikiname'] = wikiname
                fields['pagename'] = pagename
                fields['attachment'] = attachmentname
                fields['mtime'] = str(mtime)
                fields['revision'] = '0'
                fields['title'] = '%s/%s' % (pagename, attachmentname)
                fields['content'] = att_content
                fields['lang'], fields['stem_lang'] = self._get_languages(page)

                multivalued_fields = {}
                multivalued_fields['mimetype'] = [mt for mt in [mimetype] + mimetype.split('/')]
                multivalued_fields['domain'] = self._get_domains(page)

                self._add_fields_to_document(request, doc, fields, multivalued_fields)

                connection.replace(doc)
                logging.debug('attachment %s (page %s) updated in index' % (attachmentname, pagename))
        else:
            # attachment file was deleted, remove it from index also
            connection.delete(itemid)
            logging.debug('attachment %s (page %s) removed from index' % (attachmentname, pagename))

    def _index_file(self, request, connection, filename, mode='update'):
        """ index files (that are NOT attachments, just arbitrary files)

        @param request: request suitable for indexing
        @param connection: the Indexer connection object
        @param filename: a filesystem file name
        @param mode: 'add' = just add, no checks
                     'update' = check if already in index and update if needed (mtime)
        """
        wikiname = app.cfg.interwikiname or u"Self"
        fs_rootpage = 'FS' # XXX FS hardcoded

        try:
            itemid = "%s:%s" % (wikiname, os.path.join(fs_rootpage, filename))
            mtime = wikiutil.timestamp2version(os.path.getmtime(filename))

            doc = self._get_document(connection, itemid, mtime, mode)
            logging.debug("%s %r" % (filename, doc))
            if doc:
                mimetype, file_content = self.contentfilter(filename)

                fields = {}
                fields['wikiname'] = wikiname
                fields['pagename'] = fs_rootpage
                fields['attachment'] = filename # XXX we should treat files like real pages, not attachments
                fields['mtime'] = str(mtime)
                fields['revision'] = '0'
                fields['title'] = " ".join(os.path.join(fs_rootpage, filename).split("/"))
                fields['content'] = file_content

                multivalued_fields = {}
                multivalued_fields['mimetype'] = [mt for mt in [mimetype] + mimetype.split('/')]

                self._add_fields_to_document(request, doc, fields, multivalued_fields)

                connection.replace(doc)

        except (OSError, IOError, UnicodeError):
            logging.exception("_index_file crashed:")

    def _index_pages(self, request, files=None, mode='update', pages=None):
        """ Index all (given) pages (and all given files)

        This should be called from indexPages only!

        @param request: request suitable for indexing
        @param files: an optional list of files to index
        @param mode: 'add' = just add, no checks
                     'update' = check if already in index and update if needed (mtime)
        @param pages: list of pages to index, if not given, all pages are indexed
        """
        if pages is None:
            # Index all pages
            pages = request.rootpage.getPageList(user='', exists=1)

        try:
            connection = self.get_indexer_connection()
            self.touch()
            try:
                logging.info("indexing %d pages..." % len(pages))
                for pagename in pages:
                    self._index_page(request, connection, pagename, mode=mode)
                if files:
                    logging.info("indexing all files...")
                    for fname in files:
                        fname = fname.strip()
                        self._index_file(request, connection, fname, mode)
            finally:
                connection.close()
        except XapianDatabaseLockError:
            logging.warning("xapian index is locked, can't index.")

