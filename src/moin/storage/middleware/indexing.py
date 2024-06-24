# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:MichaelMayorov
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - indexing middleware

The backends and stores moin uses are rather simple, it is mostly just a
unsorted / unordered bunch of revisions (meta and data) with iteration.

The indexer middleware adds the needed power: after all metadata and data
is indexed, we can do all sorts of operations on the indexer level:
* searching
* lookup by name, uuid, ...
* selecting
* listing

Using Whoosh (a fast pure-Python indexing and search library), we build,
maintain and use 2 indexes:

* "all revisions" index (big, needed for history search)
* "latest revisions" index (smaller, just the current revisions)

When creating or destroying revisions, indexes are automatically updated.

There is also code to do a full index rebuild in case it gets damaged, lost
or needs rebuilding for other reasons. There is also index update code to
do a quick "intelligent" update of a "mostly ok" index, that just adds,
updates, deletes stuff that is different in backend compared to current index.

Indexing is the only layer that can easily deal with **names** (it can
easily translate names to UUIDs and vice versa) and with **items** (it
knows current revision, it can easily list and order historial revisions),
using the index.

The layers below are using UUIDs to identify revisions meta and data:

* revid (metaid) - a UUID identifying a specific revision (revision metadata)
* dataid - a UUID identifying some specific revision data (optional), it is
  just stored into revision metadata.
* itemid - a UUID identifying an item (== a set of revisions), it is just
  stored into revision metadata. itemid is only easily usable on indexing
  level.

Many methods provided by the indexing middleware will be fast, because they
will not access the layers below (like the backend), but just the index files,
usually it is even just the small and thus quick latest-revs index.
"""

import gc
import os
import sys
import shutil
import time

from collections.abc import Mapping

from flask import request
from flask import g as flaskg
from flask import current_app as app

from whoosh.fields import Schema, TEXT, ID, NUMERIC, DATETIME, KEYWORD, BOOLEAN, NGRAMWORDS
from whoosh.writing import AsyncWriter
from whoosh.qparser import QueryParser, MultifieldParser, RegexPlugin, PseudoFieldPlugin
from whoosh.qparser import WordNode
from whoosh.query import And, Every, Prefix, Term
from whoosh.sorting import FieldFacet

from moin.constants.keys import *  # noqa
from moin.constants.contenttypes import CONTENTTYPE_USER

from moin import user
from moin.search.analyzers import item_name_analyzer, MimeTokenizer, AclTokenizer
from moin.themes import utctimestamp
from moin.storage.middleware.validation import ContentMetaSchema, UserMetaSchema, validate_data
from moin.storage.error import NoSuchItemError, ItemAlreadyExistsError
from moin.utils import utcfromtimestamp
from moin.utils.interwiki import split_fqname, CompositeName
from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import moin_page
from moin.converters import default_registry
from moin.utils.iri import Iri
from moin.i18n import _

from moin import log

logging = log.getLogger(__name__)


WHOOSH_FILESTORAGE = "FileStorage"
INDEXES = [LATEST_REVS, ALL_REVS]

VALIDATION_HANDLING_STRICT = "strict"
VALIDATION_HANDLING_WARN = "warn"
# TODO: fix tests to create valid metadata
VALIDATION_HANDLING = VALIDATION_HANDLING_WARN if "pytest" in sys.modules else VALIDATION_HANDLING_STRICT

INDEXER_TIMEOUT = 20.0


def get_indexer(fn, **kw):
    """
    Return a valid indexer or raise a KeyError.

    Under heavy loads, the Whoosh AsyncWriter writer may be delayed in writing
    indexes to storage. Try several times before failing.

    FIXME: runs into timeout for a non-existing revid

    :param fn: the indexer function
    :param **kw: "revid" is required, index name optional
    """
    until = time.time() + INDEXER_TIMEOUT
    while True:
        indexer = fn(**kw)
        if indexer is not None:
            break
        time.sleep(2)
        if time.time() > until:
            raise KeyError(kw.get("revid", "") + " - server overload or corrupt index")
    return indexer


def parent_names(names):
    """
    Compute list of parent names (same order as in names, but no dupes)

    :param names: item NAME from whoosh index, where NAME is a list
    :return: parent names list
    """
    parents = set()
    for name in names:
        parent_tail = name.rsplit("/", 1)
        if len(parent_tail) == 2:
            parents.add(parent_tail[0])
    return parents


def search_names(name_prefix, limit=None):
    """
    get list of item names beginning with name_prefix

    :param name_prefix: item NAME prefix
    :param limit: limit number of search results
    :return: item names list
    """

    idx_name = LATEST_REVS
    terms = [Prefix(NAME_EXACT, name_prefix)]
    terms.append(Term(WIKINAME, app.cfg.interwikiname))
    q = And(terms)
    with flaskg.storage.indexer.ix[idx_name].searcher() as searcher:
        results = searcher.search(q, limit=limit)
        result_names = [result[NAME][0] for result in results]
    return result_names


def backend_to_index(meta, content, schema, wikiname, backend_name):
    """
    Convert backend metadata/data to a whoosh document.

    :param meta: revision meta from moin backend
    :param content: revision data converted to indexable content
    :param schema: whoosh schema
    :param wikiname: interwikiname of this wiki
    :returns: document to put into whoosh index
    """
    doc = {key: value for key, value in meta.items() if key in schema}
    if SUBSCRIPTION_IDS in schema and SUBSCRIPTIONS in meta:
        doc[SUBSCRIPTION_IDS], doc[SUBSCRIPTION_PATTERNS] = backend_subscriptions_to_index(meta[SUBSCRIPTIONS])
    for key in [MTIME, PTIME]:
        if key in doc:
            # we have UNIX UTC timestamp (int), whoosh wants datetime
            doc[key] = utcfromtimestamp(doc[key])
    doc[NAME_EXACT] = doc[NAME]
    doc[WIKINAME] = wikiname
    doc[CONTENT] = content
    doc[BACKENDNAME] = backend_name
    if CONTENTNGRAM in schema:
        doc[CONTENTNGRAM] = content
    if SUMMARYNGRAM in schema and SUMMARY in meta:
        doc[SUMMARYNGRAM] = meta[SUMMARY]
    if NAMENGRAM in schema and NAME in meta:
        doc[NAMENGRAM] = " ".join(meta[NAME])
    if doc.get(TAGS, None):
        # global tags uses this to search for items with tags
        doc[HAS_TAG] = True
    if doc.get(NAME, None):
        if doc.get(NAMESPACE, None):
            fullnames = [doc[NAMESPACE] + "/" + x for x in doc[NAME]]
            doc[NAMES] = " | ".join(fullnames)
        else:
            doc[NAMES] = " | ".join(doc[NAME])
        doc[NAME_SORT] = doc[NAMES].replace("/", "")
    else:
        doc[NAME_SORT] = ""
    return doc


def backend_subscriptions_to_index(subscriptions):
    """Split subscriptions list to subscription_ids and subscription_patterns lists
    which match the fields of the whoosh schema

    :param subscriptions: user subscriptions meta
    :return: tuple containing a list of subscription_ids and a list of
             subscription_patterns
    """
    subscription_ids = []
    subscription_patterns = []
    for subscription in subscriptions:
        keyword = subscription.split(":")[0]
        if keyword in (ITEMID, NAME, TAGS):
            subscription_ids.append(subscription)
        elif keyword in (NAMERE, NAMEPREFIX):
            subscription_patterns.append(subscription)
    return subscription_ids, subscription_patterns


def convert_to_indexable(meta, data, item_name=None, is_new=False):
    """
    Convert revision data to a indexable content.

    :param meta: revision metadata (gets updated as a side effect)
    :param data: revision data (file-like)
                 please make sure that the content file is
                 ready to read all indexable content from it. if you have just
                 written that content or already read from it, you need to call
                 rev.seek(0) before calling convert_to_indexable(rev).
    :param is_new: if this is for a new revision and we shall modify
                   metadata as a side effect
    :returns: indexable content, text/plain, unicode object
    """
    if not item_name:
        try:
            item_name = meta[NAMESPACE] + "/" + meta[NAME][0]
        except IndexError:
            item_name = meta[NAMESPACE] + "/" + "DoesNotExist"
    elif item_name and meta.get(NAMESPACE):
        item_name = meta[NAMESPACE] + "/" + meta[NAME][0]
    fqname = split_fqname(item_name)

    class PseudoRev:
        def __init__(self, meta, data):
            self.meta = meta
            self.data = data
            self.revid = meta.get(REVID)

            class PseudoItem:
                def __init__(self, fqname):
                    self.fqname = fqname
                    self.name = fqname.value

            self.item = PseudoItem(fqname)

        def read(self, *args, **kw):
            return self.data.read(*args, **kw)

        def seek(self, *args, **kw):
            return self.data.seek(*args, **kw)

        def tell(self, *args, **kw):
            return self.data.tell(*args, **kw)

    if meta[CONTENTTYPE] in app.cfg.mimetypes_to_index_as_empty:
        logging.debug(f"not indexing content of {meta[NAME]!r} as requested by configuration")
        return ""

    rev = PseudoRev(meta, data)
    try:
        # TODO use different converter mode?
        # Maybe we want some special mode for the input converters so they emit
        # different output than for normal rendering), esp. for the non-markup
        # content types (images, etc.).
        input_contenttype = meta[CONTENTTYPE]
        output_contenttype = "text/plain"
        type_input_contenttype = Type(input_contenttype)
        type_output_contenttype = Type(output_contenttype)
        reg = default_registry
        # first try a direct conversion (this could be useful for extraction
        # of (meta)data from binary types, like from images or audio):
        conv = reg.get(type_input_contenttype, type_output_contenttype)
        if conv:
            doc = conv(rev, input_contenttype)
            return doc
        # otherwise try via DOM as intermediate format (this is useful if
        # input type is markup, to get rid of the markup):
        input_conv = reg.get(type_input_contenttype, type_moin_document)
        refs_conv = reg.get(type_moin_document, type_moin_document, items="refs")
        output_conv = reg.get(type_moin_document, type_output_contenttype)
        if input_conv and output_conv:
            doc = input_conv(rev, input_contenttype)
            # We do not convert smileys, includes, macros, links, because
            # it does not improve search results or even makes results worse.
            # We do run the referenced converter, though, to extract links and
            # transclusions.
            if is_new:
                # we only can modify new, uncommitted revisions, not stored revs
                i = Iri(scheme="wiki", authority="", path="/" + item_name)
                doc.set(moin_page.page_href, str(i))
                refs_conv(doc)
                # side effect: we update some metadata:
                meta[ITEMLINKS] = sorted(refs_conv.get_links())
                meta[ITEMTRANSCLUSIONS] = sorted(refs_conv.get_transclusions())
                meta[EXTERNALLINKS] = sorted(refs_conv.get_external_links())
            doc = output_conv(doc)
            return doc
        # no way
        raise TypeError(f"No converter for {input_contenttype} --> {output_contenttype}")
    except Exception as e:  # catch all exceptions, we don't want to break an indexing run
        logging.exception(
            "Exception happened in conversion of item {!r} rev {} contenttype {}:".format(
                item_name, meta.get(REVID, "new"), meta.get(CONTENTTYPE, "")
            )
        )
        doc = f"ERROR [{e!s}]"
        return doc


class IndexingMiddleware:
    def __init__(self, index_storage, backend, wiki_name=None, acl_rights_contents=[], **kw):
        """
        Store params, create schemas.

        See https://whoosh.readthedocs.io/en/latest/schema.html#built-in-field-types
        """
        self.index_storage = index_storage
        self.backend = backend
        self.wikiname = wiki_name
        self.ix = {}  # open indexes
        self.schemas = {}  # existing schemas

        # field_boosts favor hits on names, tags, summary, comment, content, namengram,
        # summaryngram and contentngram respectively
        # when query_parser default search includes [NAMES, NAMENGRAM, TAGS, SUMMARY,
        # SUMMARYNGRAM, CONTENT, CONTENTNGRAM, COMMENT].
        # Note *NGRAMS are only present in latest_revs index, see below
        common_fields = {
            # wikiname so we can have a shared index in a wiki farm, always check this!
            WIKINAME: ID(stored=True),
            # namespace, so we can have different namespaces within a wiki, always check this!
            NAMESPACE: ID(stored=True),
            # since name is a list whoosh will think it is a list of tokens see #364
            # we store list of names, but do not use for searching
            NAME: TEXT(stored=True),
            # string created by joining list of Name strings, we use NAMES for searching
            NAMES: TEXT(stored=True, multitoken_query="or", analyzer=item_name_analyzer(), field_boost=30.0),
            # names without slashes, slashes cause strange sort sequences
            NAME_SORT: TEXT(stored=True),
            # unmodified NAME from metadata - use this for precise lookup by the code.
            # also needed for wildcard search, so the original string as well as the query
            # (with the wildcard) is not cut into pieces.
            NAME_EXACT: ID(field_boost=1.0),
            # history and mychanges views show old name for deleted items
            NAME_OLD: TEXT(stored=True),
            # revision id (aka meta id)
            REVID: ID(unique=True, stored=True),
            # sequential revision number for humans: 1, 2, 3...
            REV_NUMBER: NUMERIC(stored=True),
            # parent revision id
            PARENTID: ID(stored=True),
            # backend name (which backend is this rev stored in?)
            BACKENDNAME: ID(stored=True),
            # MTIME from revision metadata (converted to UTC datetime)
            MTIME: DATETIME(stored=True),
            # ITEMTYPE from metadata, always matched exactly hence ID
            ITEMTYPE: ID(stored=True),
            # tokenized CONTENTTYPE from metadata
            CONTENTTYPE: TEXT(stored=True, multitoken_query="and", analyzer=MimeTokenizer()),
            # unmodified list of TAGS from metadata
            TAGS: KEYWORD(stored=True, commas=True, scorable=True, field_boost=30.0),
            # search on HAS_TAG improves response time of global tags
            # https://whoosh.readthedocs.io/en/latest/api/query.html?highlight=#whoosh.query.Every
            HAS_TAG: BOOLEAN(stored=False),
            LANGUAGE: ID(stored=True),
            # USERID from metadata
            USERID: ID(stored=True),
            # ADDRESS from metadata
            ADDRESS: ID(stored=True),
            # HOSTNAME from metadata
            HOSTNAME: ID(stored=True),
            # SIZE from metadata
            SIZE: NUMERIC(stored=True),
            # ACTION from metadata
            ACTION: ID(stored=True),
            # tokenized COMMENT from metadata
            COMMENT: TEXT(stored=True, field_boost=30.0),
            # SUMMARY from metadata
            SUMMARY: TEXT(stored=True, field_boost=10.0),
            # DATAID from metadata
            DATAID: ID(stored=True),
            # TRASH from metadata
            TRASH: BOOLEAN(stored=True),
            # data (content), converted to text/plain and tokenized
            CONTENT: TEXT(stored=True, spelling=True),
        }

        latest_revs_fields = {
            # ITEMID from metadata - as there is only latest rev of same item here, it is unique
            ITEMID: ID(unique=True, stored=True),
            # unmodified list of ITEMLINKS from metadata
            ITEMLINKS: ID(stored=True),
            # unmodified list of ITEMTRANSCLUSIONS from metadata
            ITEMTRANSCLUSIONS: ID(stored=True),
            # tokenized ACL from metadata
            ACL: TEXT(analyzer=AclTokenizer(acl_rights_contents), multitoken_query="and", stored=True),
            # index ngrams of words, field_boosts favor hits on name and summary over content
            CONTENTNGRAM: NGRAMWORDS(minsize=3, maxsize=6, queryor=True, field_boost=0.01),
            SUMMARYNGRAM: NGRAMWORDS(minsize=3, maxsize=6, queryor=True, field_boost=1.0),
            NAMENGRAM: NGRAMWORDS(minsize=3, maxsize=6, queryor=True, field_boost=1.0),
        }
        latest_revs_fields.update(**common_fields)

        userprofile_fields = {
            # Note: email (if given) should be unique, but we might
            # have lots of empty values if it is not given and thus it is NOT
            # unique overall! Wrongly declaring it unique would lead to whoosh
            # killing other users from index when update_document() is called!
            EMAIL: ID(stored=True),
            MAILTO_AUTHOR: BOOLEAN(stored=True),
            DISABLED: BOOLEAN(stored=True),
            LOCALE: ID(stored=True),
            SUBSCRIPTION_IDS: ID(),
            SUBSCRIPTION_PATTERNS: ID(),
        }
        latest_revs_fields.update(**userprofile_fields)

        # XXX This is a highly adhoc way to support indexing of ticket items.
        ticket_fields = {
            EFFORT: NUMERIC(stored=True),
            DIFFICULTY: NUMERIC(stored=True),
            SEVERITY: NUMERIC(stored=True),
            PRIORITY: NUMERIC(stored=True),
            ASSIGNED_TO: ID(stored=True),
            REPLY_TO: ID(stored=True),
            REFERS_TO: ID(stored=True),
            ELEMENT: ID(stored=True),
            SUPERSEDED_BY: ID(stored=True),
            DEPENDS_ON: ID(stored=True),
            CLOSED: BOOLEAN(stored=True),
        }
        latest_revs_fields.update(**ticket_fields)

        blog_entry_fields = {
            # blog publish time from metadata (converted to UTC datetime)
            PTIME: DATETIME(stored=True)
        }
        latest_revs_fields.update(**blog_entry_fields)

        all_revs_fields = {ITEMID: ID(stored=True)}
        all_revs_fields.update(**common_fields)

        latest_revisions_schema = Schema(**latest_revs_fields)
        all_revisions_schema = Schema(**all_revs_fields)

        # schemas are needed by query parser and for index creation
        self.schemas[ALL_REVS] = all_revisions_schema
        self.schemas[LATEST_REVS] = latest_revisions_schema

        # Define dynamic fields
        dynamic_fields = [
            ("*_id", ID(stored=True)),
            ("*_text", TEXT(stored=True)),
            ("*_keyword", KEYWORD(stored=True)),
            ("*_numeric", NUMERIC(stored=True)),
            ("*_datetime", DATETIME(stored=True)),
            ("*_boolean", BOOLEAN(stored=True)),
        ]

        # Adding dynamic fields to schemas
        for glob, field_type in dynamic_fields:
            latest_revisions_schema.add(glob, field_type, glob=True)
            all_revisions_schema.add(glob, field_type, glob=True)

        # what fields could whoosh result documents have (no matter whether all revs index
        # or latest revs index):
        self.common_fields = set(latest_revs_fields.keys()) & set(all_revs_fields.keys())

    def get_storage_params(self, tmp=False):
        kind, params, kw = self.index_storage
        params, kw = list(params), dict(kw)  # better make a (mutable) copy
        if kind == WHOOSH_FILESTORAGE:
            # index_storage = 'FileStorage', (index_dir, ), {}
            if tmp:
                params[0] += ".temp"
            from whoosh.filedb.filestore import FileStorage

            cls = FileStorage
        else:
            raise ValueError(f"index_storage = {kind!r} is not supported!")
        return kind, cls, params, kw

    def get_storage(self, tmp=False, create=False):
        """
        Get the whoosh storage (whoosh supports different kinds of storage,
        e.g. to filesystem or to GAE).
        Currently we only support the FileStorage.
        """
        kind, cls, params, kw = self.get_storage_params(tmp)

        if kind == WHOOSH_FILESTORAGE:
            if create:
                index_dir = params[0]
                try:
                    logging.debug("os.mkdir(%s)", str(index_dir))
                    os.mkdir(index_dir)
                except FileExistsError:
                    logging.debug("os.mkdir() failed: FileExistsError will be ignored.")
                    # ignore exception, we'll get another exception below
                    # in case there are problems with the index_dir
        return cls(*params, **kw)

    def open(self):
        """
        Open all indexes.
        """
        storage = self.get_storage()
        for name in INDEXES:
            self.ix[name] = storage.open_index(name)

    def close(self):
        """
        Close all indexes.
        """
        for name in self.ix:
            self.ix[name].close()
        self.ix = {}

    def create(self, tmp=False):
        """
        Create all indexes (empty).
        """
        storage = self.get_storage(tmp, create=True)
        for name in INDEXES:
            storage.create_index(self.schemas[name], indexname=name)

    def destroy(self, tmp=False):
        """
        Destroy all indexes.
        """
        # XXX this is whoosh backend specific and currently only works for FileStorage.
        kind, cls, params, kw = self.get_storage_params(tmp)
        if kind == WHOOSH_FILESTORAGE:
            index_dir = params[0]
            if os.path.exists(index_dir):
                shutil.rmtree(index_dir)

    def move_index(self):
        """
        Move freshly built indexes from tmp storage to normal storage
        """
        # XXX this is whoosh backend specific and currently only works for FileStorage.
        kind, cls, params, kw = self.get_storage_params(False)
        if kind == WHOOSH_FILESTORAGE:
            _, _, params_tmp, _ = self.get_storage_params(True)
            self.destroy()
            index_dir, index_dir_tmp = params[0], params_tmp[0]
            os.rename(index_dir_tmp, index_dir)

    def index_revision(self, meta, content, backend_name, async_=True, force_latest=True):
        """
        Index a single revision, add it to all-revs and latest-revs index.

        :param meta: metadata dict
        :param content: preprocessed (filtered) indexable content
        :param async_: if True, use the AsyncWriter, otherwise use normal writer
        :param force_latest: True - unconditionally store this rev in LATEST_REVS
                             False - store in LATEST_REVS if this rev MTIME is most recent
                                     overrides async_ parameter to False
        """
        if not force_latest:
            async_ = False  # must wait for storage in ALL_REVS before check for latest
        doc = backend_to_index(meta, content, self.schemas[ALL_REVS], self.wikiname, backend_name)
        if async_:
            writer = AsyncWriter(self.ix[ALL_REVS])
        else:
            writer = self.ix[ALL_REVS].writer()
        with writer as writer:
            writer.update_document(**doc)  # update, because store_revision() may give us an existing revid
        if force_latest:
            is_latest = True
        else:
            with self.ix[ALL_REVS].searcher() as searcher:
                is_latest = (
                    searcher.search(Term(ITEMID, doc[ITEMID]), sortedby=FieldFacet(MTIME, reverse=True), limit=1)[0][
                        REVID
                    ]
                    == doc[REVID]
                )
        if is_latest:
            doc = backend_to_index(meta, content, self.schemas[LATEST_REVS], self.wikiname, backend_name)
            if async_:
                writer = AsyncWriter(self.ix[LATEST_REVS])
            else:
                writer = self.ix[LATEST_REVS].writer()
            with writer as writer:
                writer.update_document(**doc)

    def remove_revision(self, revid, async_=True):
        """
        Remove a single revision from indexes.
        """
        if async_:
            writer = AsyncWriter(self.ix[ALL_REVS])
        else:
            writer = self.ix[ALL_REVS].writer()
        with writer as writer:
            writer.delete_by_term(REVID, revid)
        if async_:
            writer = AsyncWriter(self.ix[LATEST_REVS])
        else:
            writer = self.ix[LATEST_REVS].writer()
        with writer as writer:
            # find out itemid related to the revid we want to remove:
            with self.ix[LATEST_REVS].searcher() as searcher:
                docnum_remove = searcher.document_number(revid=revid)
                if docnum_remove is not None:
                    itemid = searcher.stored_fields(docnum_remove)[ITEMID]
            if docnum_remove is not None:
                # we are removing a revid that is in latest revs index
                latest_backends_revids = self._find_latest_backends_revids(self.ix[ALL_REVS], Term(ITEMID, itemid))
                if latest_backends_revids:
                    # we have a latest revision, just update the document in the index:
                    assert len(latest_backends_revids) == 1  # this item must have only one latest revision
                    latest_backend_revid = latest_backends_revids[0]
                    # we must fetch from backend because schema for LATEST_REVS is different than for ALL_REVS
                    # (and we can't be sure we have all fields stored, too)
                    meta, _ = self.backend.retrieve(*latest_backend_revid)
                    # we only use meta (not data), because we do not want to transform data->content again (this
                    # is potentially expensive) as we already have the transformed content stored in ALL_REVS index:
                    with self.ix[ALL_REVS].searcher() as searcher:
                        doc = searcher.document(revid=latest_backend_revid[1])
                        content = doc[CONTENT]
                    doc = backend_to_index(
                        meta, content, self.schemas[LATEST_REVS], self.wikiname, backend_name=latest_backend_revid[0]
                    )
                    writer.update_document(**doc)
                else:
                    # this is no revision left in this item that could be the new "latest rev", just kill the rev
                    writer.delete_document(docnum_remove)

    def _modify_index(self, index, schema, wikiname, revids, mode="add", procs=1, limitmb=256):
        """
        modify index contents - add, update, delete the indexed documents for all given revids

        Note: mode == 'add' is faster but you need to make sure to not create duplicate
              documents in the index.
        """
        with index.writer(procs=procs, limitmb=limitmb) as writer:
            for backend_name, revid in revids:
                if mode in ["add", "update"]:
                    meta, data = self.backend.retrieve(backend_name, revid)
                    content = convert_to_indexable(meta, data, is_new=False)
                    doc = backend_to_index(meta, content, schema, wikiname, backend_name)
                if mode == "update":
                    writer.update_document(**doc)
                elif mode == "add":
                    writer.add_document(**doc)
                elif mode == "delete":
                    writer.delete_by_term(REVID, revid)
                else:
                    raise ValueError(f"mode must be 'update', 'add' or 'delete', not '{mode}'")

    def _find_latest_backends_revids(self, index, query=None):
        """
        find the latest revision identifiers using the all-revs index

        :param index: an up-to-date and open ALL_REVS index
        :param query: query to search only specific revisions (optional, default: all items/revisions)
        :returns: a list of tuples (backend name, latest revid)
        """
        if query is None:
            query = Every()
        with index.searcher() as searcher:
            result = searcher.search(query, groupedby=ITEMID, sortedby=FieldFacet(MTIME, reverse=True))
            by_item = result.groups(ITEMID)
            # values in v list are in same relative order as in results, so latest MTIME is first:
            latest_backends_revids = [
                (searcher.stored_fields(v[0])[BACKENDNAME], searcher.stored_fields(v[0])[REVID])
                for v in by_item.values()
            ]
        return latest_backends_revids

    def rebuild(self, tmp=False, procs=1, limitmb=256):
        """
        Add all items/revisions from the backends of this wiki to the index
        (which is expected to have no items/revisions from this wiki yet).

        Note: index might be shared by multiple wikis, so it is:
              create, rebuild wiki1, rebuild wiki2, ...
              create (tmp), rebuild wiki1, rebuild wiki2, ..., move
        """
        storage = self.get_storage(tmp)
        index = storage.open_index(ALL_REVS)
        try:
            # build an index of all we have (so we know what we have)
            all_revids = self.backend  # the backend is an iterator over all revids
            self._modify_index(index, self.schemas[ALL_REVS], self.wikiname, all_revids, "add", procs, limitmb)
            latest_backends_revids = self._find_latest_backends_revids(index)
        finally:
            index.close()

        # now build the index of the latest revisions:
        index = storage.open_index(LATEST_REVS)
        try:
            self._modify_index(
                index, self.schemas[LATEST_REVS], self.wikiname, latest_backends_revids, "add", procs, limitmb
            )
        finally:
            index.close()

    def update(self, tmp=False):
        """
        Make sure index reflects current backend state, add missing stuff, remove outdated stuff.

        This is intended to be used:
        * after a full rebuild that was done at tmp location
        * after wiki is made read-only or taken offline
        * after the index was moved to the normal index location

        Reason: new revisions that were created after the rebuild started might be missing in new index.

        :returns: index changed (bool)
        """
        storage = self.get_storage(tmp)
        index_all = storage.open_index(ALL_REVS)
        try:
            # NOTE: self.backend iterator gives (backend_name, revid) tuples, which is NOT
            # the same as (name, revid), thus we do the set operations just on the revids.
            # first update ALL_REVS index:
            revids_backends = {revid: backend_name for backend_name, revid in self.backend}
            backend_revids = set(revids_backends)
            with index_all.searcher() as searcher:
                ix_revids_backends = {doc[REVID]: doc[BACKENDNAME] for doc in searcher.all_stored_fields()}
            revids_backends.update(ix_revids_backends)  # this is needed for stuff that was deleted from storage
            ix_revids = set(ix_revids_backends)
            add_revids = backend_revids - ix_revids
            del_revids = ix_revids - backend_revids
            changed = add_revids or del_revids
            add_revids = [(revids_backends[revid], revid) for revid in add_revids]
            del_revids = [(revids_backends[revid], revid) for revid in del_revids]
            self._modify_index(index_all, self.schemas[ALL_REVS], self.wikiname, add_revids, "add")
            self._modify_index(index_all, self.schemas[ALL_REVS], self.wikiname, del_revids, "delete")

            backend_latest_backends_revids = set(self._find_latest_backends_revids(index_all))
        finally:
            index_all.close()
        index_latest = storage.open_index(LATEST_REVS)
        try:
            # now update LATEST_REVS index:
            with index_latest.searcher() as searcher:
                ix_revids = {doc[REVID] for doc in searcher.all_stored_fields()}
            backend_latest_revids = {revid for name, revid in backend_latest_backends_revids}
            upd_revids = backend_latest_revids - ix_revids
            upd_revids = [(revids_backends[revid], revid) for revid in upd_revids]
            self._modify_index(index_latest, self.schemas[LATEST_REVS], self.wikiname, upd_revids, "update")
            self._modify_index(index_latest, self.schemas[LATEST_REVS], self.wikiname, del_revids, "delete")
        finally:
            index_latest.close()
        return changed

    def optimize_backend(self):
        """
        Optimize backend / collect garbage to safe space:

        * deleted items: destroy them? use a deleted_max_age?
        * user profiles: only keep latest revision?
        * normal wiki items: keep by max_revisions_count / max_age
        * deduplicate data (determine dataids with same hash, fix references to point to one of them)
        * remove unreferenced dataids (destroyed revisions, deduplicated stuff)
        """
        # TODO

    def optimize_index(self, tmp=False):
        """
        Optimize whoosh index.
        """
        storage = self.get_storage(tmp)
        for name in INDEXES:
            ix = storage.open_index(name)
            try:
                ix.optimize()
            finally:
                ix.close()

    def dump(self, tmp=False, idx_name=LATEST_REVS):
        """
        Yield key/value tuple lists for all documents in the indexes, fields sorted.
        """
        storage = self.get_storage(tmp)
        ix = storage.open_index(idx_name)
        while not ix.up_to_date():
            logging.info("waiting for ix.up_to_date()")
            time.sleep(0.1)
        try:
            with ix.searcher() as searcher:
                for doc in searcher.all_stored_fields():
                    name = doc.pop(NAME, "")
                    content = doc.pop(CONTENT, "")
                    yield [(NAME, name)] + sorted(doc.items()) + [(CONTENT, content)]
        finally:
            ix.close()

    def query_parser(self, default_fields, idx_name=LATEST_REVS):
        """
        Build a query parser for a list of default fields.
        """
        schema = self.schemas[idx_name]
        if len(default_fields) > 1:
            qp = MultifieldParser(default_fields, schema=schema)
        elif len(default_fields) == 1:
            qp = QueryParser(default_fields[0], schema=schema)
        else:
            raise ValueError("default_fields list must at least contain one field name")
        qp.add_plugin(RegexPlugin())

        def userid_pseudo_field_factory(fieldname):
            """generate a translator function, that searches for the userid
            in the given fieldname when provided with the username
            """

            def userid_pseudo_field(node):
                username = node.text
                users = user.search_users(**{NAME_EXACT: username})
                if users:
                    userid = users[0].meta[ITEMID]
                    node = WordNode(userid)
                    node.set_fieldname(fieldname)
                    return node
                return node

            return userid_pseudo_field

        qp.add_plugin(
            PseudoFieldPlugin(
                dict(
                    # username:JoeDoe searches for revisions modified by JoeDoe
                    username=userid_pseudo_field_factory(USERID),
                    # assigned:JoeDoe searches for tickets assigned to JoeDoe
                    assigned=userid_pseudo_field_factory(ASSIGNED_TO),
                )
            )
        )
        return qp

    def search(self, q, idx_name=LATEST_REVS, **kw):
        """
        Search with query q, yield Revisions.
        """
        with self.ix[idx_name].searcher() as searcher:
            # Note: callers must consume everything we yield, so the for loop
            # ends and the "with" is left to close the index files.
            for hit in searcher.search(q, **kw):
                doc = hit.fields()
                latest_doc = doc if idx_name == LATEST_REVS else None
                item = Item(self, latest_doc=latest_doc, itemid=doc[ITEMID])
                yield item.get_revision(doc[REVID], doc=doc)

    def search_page(self, q, idx_name=LATEST_REVS, pagenum=1, pagelen=10, **kw):
        """
        Same as search, but with paging support.
        """
        with self.ix[idx_name].searcher() as searcher:
            # Note: callers must consume everything we yield, so the for loop
            # ends and the "with" is left to close the index files.
            for hit in searcher.search_page(q, pagenum, pagelen=pagelen, **kw):
                doc = hit.fields()
                latest_doc = doc if idx_name == LATEST_REVS else None
                item = Item(self, latest_doc=latest_doc, itemid=doc[ITEMID])
                yield item.get_revision(doc[REVID], doc=doc)

    def search_meta(self, q, idx_name=LATEST_REVS, **kw):
        """
        Search with query q, yield Revision metadata from index.
        """
        with self.ix[idx_name].searcher() as searcher:
            # Note: callers must consume everything we yield, so the for loop
            # ends and the "with" is left to close the index files.
            for hit in searcher.search(q, **kw):
                meta = hit.fields()
                yield meta

    def search_meta_page(self, q, idx_name=LATEST_REVS, pagenum=1, pagelen=10, **kw):
        """
        Same as search_meta, but with paging support.
        """
        with self.ix[idx_name].searcher() as searcher:
            # Note: callers must consume everything we yield, so the for loop
            # ends and the "with" is left to close the index files.
            for hit in searcher.search_page(q, pagenum, pagelen=pagelen, **kw):
                meta = hit.fields()
                yield meta

    def search_results_size(self, q, idx_name=ALL_REVS, **kw):
        """
        Return the number of matching revisions.
        """
        with self.ix[idx_name].searcher() as searcher:
            return len(searcher.search(q, **kw))

    def documents(self, idx_name=LATEST_REVS, **kw):
        """
        Yield Revisions matching the kw args.
        """
        for doc in self._documents(idx_name, **kw):
            latest_doc = doc if idx_name == LATEST_REVS else None
            item = Item(self, latest_doc=latest_doc, itemid=doc[ITEMID])
            yield item.get_revision(doc[REVID], doc=doc)

    def _documents(self, idx_name=LATEST_REVS, **kw):
        """
        Yield documents matching the kw args (internal use only).

        If no kw args are given, this yields all documents.
        """
        with self.ix[idx_name].searcher() as searcher:
            # Note: callers must consume everything we yield, so the for loop
            # ends and the "with" is left to close the index files.
            yield from searcher.documents(**kw)

    def document(self, idx_name=LATEST_REVS, **kw):
        """
        Return a Revision matching the kw args.
        """
        doc = self._document(idx_name, **kw)
        if doc:
            latest_doc = doc if idx_name == LATEST_REVS else None
            item = Item(self, latest_doc=latest_doc, itemid=doc[ITEMID])
            return item.get_revision(doc[REVID], doc=doc)

    def _document(self, idx_name=LATEST_REVS, **kw):
        """
        Return a document matching the kw args (internal use only).
        """
        with self.ix[idx_name].searcher() as searcher:
            return searcher.document(**kw)

    def has_item(self, name):
        # TODO: Add fqname support to this method
        item = self[name]
        return bool(item)

    def __getitem__(self, name):
        """
        Return item with <name> (may be a new or existing item).
        """
        if name.startswith("@itemid/"):
            return Item(self, **{ITEMID: name[8:]})
        fqname = split_fqname(name)
        return Item(self, **{NAME_EXACT: fqname.value, NAMESPACE: fqname.namespace})

    def get_item(self, **query):
        """
        Return item identified by the query (may be a new or existing item).

        :kwargs query: e.g. name_exact="Foo" or itemid="..." or ...
                     (must be a unique fieldname=value for the latest-revs index)
        """
        return Item(self, **query)

    def create_item(self, **query):
        """
        Return item identified by the query (must be a new item).

        :kwargs query: e.g. name_exact="Foo" or itemid="..." or ...
                     (must be a unique fieldname=value for the latest-revs index)
        """
        return Item.create(self, **query)

    def existing_item(self, **query):
        """
        Return item identified by query (must be an existing item).

        :kwargs query: e.g. name_exact="Foo" or itemid="..." or ...
                     (must be a unique fieldname=value for the latest-revs index)
        """
        return Item.existing(self, **query)


class PropertiesMixin:
    """
    PropertiesMixin offers methods to find out some additional information from meta.
    """

    @property
    def name(self):
        if self._name and self._name in self.names:
            name = self._name
        else:
            try:
                name = self.names[0]
            except IndexError:
                # empty name list, no name:
                name = None
        assert isinstance(name, str) or not name
        return name

    @property
    def namespace(self):
        return self.meta.get(NAMESPACE, "")

    def _fqname(self, name=None):
        """
        return the fully qualified name including the namespace: NS:NAME
        """
        if name is not None:
            return CompositeName(self.namespace, NAME_EXACT, name)
        else:
            return CompositeName(self.namespace, ITEMID, self.meta[ITEMID])

    @property
    def fqname(self):
        """
        return the fully qualified name including the namespace: NS:NAME
        """
        return self._fqname(self.name)

    @property
    def fqnames(self):
        """
        return the fully qualified names including the namespace: NS:NAME
        """
        if self.names:
            return [self._fqname(name) for name in self.names]
        else:
            return [self.fqname]

    @property
    def parentnames(self):
        """
        Return list of parent names (same order as in names, but no dupes)

        :return: parent names (list of unicode)
        """
        return parent_names(self.names)

    @property
    def fqparentnames(self):
        """
        return the fully qualified parent names including the namespace: NS:NAME
        """
        return [self._fqname(name) for name in self.parentnames]

    @property
    def acl(self):
        return self.meta.get(ACL)

    @property
    def ptime(self):
        dt = self.meta.get(PTIME)
        if dt is not None:
            return utctimestamp(dt)

    @property
    def names(self):
        return self.meta[NAME]

    @property
    def mtime(self):
        dt = self.meta.get(MTIME)
        if dt is not None:
            return utctimestamp(dt)


class Item(PropertiesMixin):
    def __init__(self, indexer, latest_doc=None, **query):
        """
        :param indexer: indexer middleware instance
        :param latest_doc: if caller already has a latest-revs index whoosh document
                           it can be given there, to avoid us fetching same doc again
                           from the index
        :kwargs **query: any unique fieldname=value for the latest-revs index, e.g.:
                         name_exact="foo" or itemid="....." to fetch the item's current
                         doc from the index (if not given via latest_doc).
        """
        self.indexer = indexer
        self.backend = self.indexer.backend
        self._name = query.get(NAME_EXACT)
        if latest_doc is None:
            # we need to call the method without acl check to avoid endless recursion:
            latest_doc = self.indexer._document(**query)
            if latest_doc is None:
                # no such item, create a dummy doc that has a NAME entry to
                # avoid issues in the name(s) property code. if this was a
                # lookup for some specific item (using a name_exact query), we
                # put that name into the NAME list, otherwise it'll be empty:
                latest_doc = {}
                for field, value in query.items():
                    latest_doc[field] = [value] if field in UFIELDS_TYPELIST else value
                latest_doc[NAME] = latest_doc[NAME_EXACT] if NAME_EXACT in query else []
        self._current = latest_doc

    def _get_itemid(self):
        return self._current.get(ITEMID)

    def _set_itemid(self, value):
        self._current[ITEMID] = value

    itemid = property(_get_itemid, _set_itemid)

    @property
    def meta(self):
        return self._current

    @property
    def parentids(self):
        """
        compute list of parent itemids

        :return: parent itemids (set)
        """
        parent_ids = set()
        for parent_name in self.parentnames:
            rev = self.indexer._document(idx_name=LATEST_REVS, **{NAME_EXACT: parent_name})
            if rev:
                parent_ids.add(rev[ITEMID])
        return parent_ids

    @classmethod
    def create(cls, indexer, **query):
        """
        Create a new item and return it, raise exception if it already exists.
        """
        item = cls(indexer, **query)
        if not item:
            return item
        raise ItemAlreadyExistsError(repr(query))

    @classmethod
    def existing(cls, indexer, **query):
        """
        Get an existing item and return it, raise exception if it does not exist.
        """
        item = cls(indexer, **query)
        if item:
            return item
        raise NoSuchItemError(repr(query))

    def __repr__(self):
        return f"<Item {self.name}>"

    def __bool__(self):
        """
        Item exists (== has at least one revision)?
        """
        return self.itemid is not None

    def iter_revs(self):
        """
        Iterate over Revisions belonging to this item.
        """
        if self:
            yield from self.indexer.documents(idx_name=ALL_REVS, itemid=self.itemid)

    def __getitem__(self, revid):
        """
        Get Revision with revision id <revid>.
        """
        return Revision(self, revid)

    def get_revision(self, revid, doc=None):
        """
        Similar to item[revid], but you can optionally give an already existing
        whoosh result document for the given revid to avoid backend accesses for some use cases.
        """
        return Revision(self, revid, doc)

    def preprocess(self, meta, data):
        """
        preprocess a revision before it gets stored and put into index.
        """
        content = convert_to_indexable(meta, data, self.name, is_new=True)
        return meta, data, content

    def store_revision(
        self,
        meta,
        data,
        overwrite=False,
        trusted=False,  # True for loading a serialized representation or other trusted sources
        name=None,  # TODO name we decoded from URL path
        action=ACTION_SAVE,
        remote_addr=None,
        userid=None,
        wikiname=None,
        contenttype_current=None,
        contenttype_guessed=None,
        acl_parent=None,
        return_rev=False,
        fqname=None,
    ):
        """
        Store a revision into the backend, write metadata and data to it.

        Usually this will be a new revision, either of an existing item or
        a new item. With overwrite mode, we can also store over existing
        revisions.

        :type meta: dict
        :type data: open file (file must be closed by caller)
        :param overwrite: if True, allow overwriting of existing revs.
        :param return_rev: if True, return a Revision instance of the just created revision
        :returns: a Revision instance or None
        """
        if remote_addr is None:
            try:
                # if we get here outside a request, this won't work:
                remote_addr = str(request.remote_addr)
            except RuntimeError:
                remote_addr = "127.0.0.1"
        if userid is None:
            try:
                # if we get here outside a request, this won't work:
                userid = flaskg.user.valid and flaskg.user.itemid or None
            except:  # noqa
                pass
        if wikiname is None:
            wikiname = app.cfg.interwikiname
        state = {
            "trusted": trusted,
            NAME: [name],
            ACTION: action,
            ADDRESS: remote_addr,
            USERID: userid,
            WIKINAME: wikiname,
            NAMESPACE: None,
            ITEMID: self.itemid,  # real itemid or None
            "contenttype_current": contenttype_current,
            "contenttype_guessed": contenttype_guessed,
            "acl_parent": acl_parent,
            FQNAME: fqname,
        }
        ct = meta.get(CONTENTTYPE)
        if ct == CONTENTTYPE_USER:
            Schema = UserMetaSchema
        else:
            Schema = ContentMetaSchema
        m = Schema(meta)
        valid = m.validate(state)
        if not valid:
            logging.warning("data validation skipped because metadata is invalid, see below")
            val = []
            for e in m.children:
                if e.name in ["itemlinks", "subscriptions"]:
                    for child in e.children:
                        if child.valid is False:
                            val.append(f'"{str(child)}". {str(child.errors[0])}')
                            e.valid = False
                elif e.valid is False:
                    val.append(str(e))
                logging.warning(f"{e.valid}, {e.name}, {e.raw}")
            if VALIDATION_HANDLING == VALIDATION_HANDLING_STRICT:
                raise ValueError(
                    _("Error: metadata validation failed, invalid field value(s) = {0}").format(", ".join(val))
                )

        # we do not have anything in m that is not defined in the schema,
        # e.g. userdefined meta keys or stuff we do not validate. thus, we
        # just update the meta dict with the validated stuff:
        meta.update(dict(m.value.items()))
        if hasattr(flaskg, "data_mtime"):
            # this is maint-reduce-revisions OR item-put CL process, restore saved time of item's last update
            meta[MTIME] = flaskg.data_mtime
            del flaskg.data_mtime
        # we do not want None / empty values:
        # XXX do not kick out empty lists before fixing NAME processing:
        meta = {k: v for k, v in meta.items() if v not in [None]}
        # file upload UI does not have a summary field
        if SUMMARY not in meta:
            meta[SUMMARY] = ""

        if valid and not validate_data(meta, data):  # need valid metadata to validate data
            logging.warning(f"data validation failed for item {meta[NAME]} ")
            if VALIDATION_HANDLING == VALIDATION_HANDLING_STRICT:
                raise ValueError(_("Error: nothing changed. Data unicode validation failed."))

        if self.itemid is None:
            self.itemid = meta[ITEMID]
        backend = self.backend
        if not overwrite:
            revid = meta.get(REVID)
            backend_name = dict(app.cfg.namespace_mapping)[meta.get(NAMESPACE, "")]
            if revid is not None and (revid in backend or (backend_name, revid) in backend):
                raise ValueError("need overwrite=True to overwrite existing revisions")
        meta, data, content = self.preprocess(meta, data)
        data.seek(0)  # rewind file
        backend_name, revid = backend.store(meta, data)
        meta[REVID] = revid
        self.indexer.index_revision(meta, content, backend_name, force_latest=not overwrite)
        gc.collect()  # triggers close of index files from is_latest search
        if not overwrite:
            self._current = get_indexer(self.indexer._document, revid=revid)
        if return_rev:
            return Revision(self, revid)

    def store_all_revisions(self, meta, data):
        """
        Store over all revisions of this item.
        """
        for rev in self.iter_revs():
            meta[REVID] = rev.revid
            self.store_revision(meta, data, overwrite=True)

    def destroy_revision(self, revid):
        """
        Destroy revision <revid>.
        """
        rev = Revision(self, revid)
        query = {DATAID: rev.meta[DATAID]}
        with flaskg.storage.indexer.ix[ALL_REVS].searcher() as searcher:
            refcount = len(list(searcher.document_numbers(**query)))
        self.backend.remove(rev.backend_name, revid, destroy_data=refcount == 1)
        self.indexer.remove_revision(revid)
        my_parent = rev.meta.get(PARENTID)
        with flaskg.storage.indexer.ix[ALL_REVS].searcher() as searcher:
            for hit in searcher.search(Term(PARENTID, revid)):
                doc = hit.fields()
                with Revision(self, doc[REVID], doc=doc) as child_rev:
                    child_meta = dict(child_rev.meta)
                    if my_parent:
                        child_meta[PARENTID] = my_parent
                    else:
                        del child_meta[PARENTID]
                    self.store_revision(child_meta, child_rev.data, overwrite=True, trusted=True)

    def destroy_all_revisions(self):
        """
        Destroy all revisions of this item.
        """
        for rev in self.iter_revs():
            self.destroy_revision(rev.revid)


class Revision(PropertiesMixin):
    """
    An existing revision (exists in the backend).
    """

    def __init__(self, item, revid, doc=None, name=None):
        is_current = revid == CURRENT
        if doc is None:
            if is_current:
                doc = item._current
            else:
                doc = get_indexer(item.indexer._document, idx_name=ALL_REVS, revid=revid)

        if is_current:
            revid = doc.get(REVID)
            if revid is None:
                raise KeyError
        self.item = item
        self.revid = revid
        self.backend = item.backend
        self.backend_name = doc[BACKENDNAME]
        self._doc = doc
        self.meta = Meta(self, self._doc)
        self._data = None
        if name and name in self.names:
            self._name = name
        else:
            self._name = None
        # Note: this does not immediately raise a KeyError for non-existing revs any more
        # If you access data or meta, it will, though.

    def set_context(self, context):
        for name in self.names:
            if name.startswith(context):
                self._name = name
                return

    def _load(self):
        meta, data = self.backend.retrieve(self.backend_name, self.revid)  # raises KeyError if rev does not exist
        self.meta = Meta(self, self._doc, meta)
        self._data = data
        return meta, data

    @property
    def data(self):
        if self._data is None:
            self._load()
        return self._data

    def close(self):
        if self._data is not None:
            self._data.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __hash__(self):
        return hash(self.meta)

    def __eq__(self, other):
        return self.meta == other.meta

    def __lt__(self, other):
        return self.meta < other.meta

    def __repr__(self):
        return f"<Revision {self.revid[:6]} of Item {self.name}>"


class Meta(Mapping):
    def __init__(self, revision, doc, meta=None):
        self.revision = revision
        self._doc = doc or {}
        self._meta = meta or {}
        self._common_fields = revision.item.indexer.common_fields

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __iter__(self):
        self._meta, _ = self.revision._load()
        return iter(self._meta)

    def __getitem__(self, key):
        if self._meta:
            # we have real metadata (e.g. from storage)
            return self._meta[key]
        elif self._doc and key in self._common_fields:
            # we have a result document from whoosh, which has quite a lot
            # of the usually wanted metadata, avoid storage access, use this.
            value = self._doc[key]
            if key in [MTIME, PTIME]:
                # whoosh has a datetime object, but we want a UNIX timestamp
                value = utctimestamp(value)
            return value
        else:
            self._meta, _ = self.revision._load()
            return self._meta[key]

    def __hash__(self):
        return hash(self[REVID])

    def __eq__(self, other):
        return self[REVID] == other[REVID]

    def __lt__(self, other):
        return self[MTIME] < other[MTIME]

    def __len__(self):
        return 0  # XXX

    def __repr__(self):
        return f"Meta _doc: {self._doc!r} _meta: {self._meta!r}"
