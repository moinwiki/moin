# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2003-2013 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:AkashSinha
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2008 MoinMoin:FlorianKrupicka
# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2001 Richard Jones <richard@bizarsoftware.com.au>
# Copyright: 2001 Juergen Hermann <jh@web.de>
# Copyright: 2023-2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - frontend views

    This shows the usual things users see when using the wiki.
"""


import os
import re
import time
import uuid
import mimetypes
import json
import threading
import urllib.request
import urllib.parse
import urllib.error
from io import BytesIO
from datetime import datetime
from datetime import timezone
from collections import namedtuple
from functools import wraps, partial

from werkzeug.utils import secure_filename

from flask import request, url_for, flash, Response, make_response, redirect, abort, jsonify, session
from flask import current_app as app
from flask import g as flaskg
from flask_babel import format_datetime
from flask_theme import get_themes_list

from flatland import Form
from flatland.validation import Validator

from markupsafe import Markup

import pytz

from whoosh import sorting
from whoosh.query import Term, Prefix, And, Or, Not, DateRange, Every
from whoosh.query.qcore import QueryError, TermNotFound
from whoosh.analysis import StandardAnalyzer

from moin.i18n import _, L_
from moin.themes import render_template, contenttype_to_class, get_editor_info
from moin.apps.frontend import frontend
from moin.forms import (
    OptionalText,
    RequiredText,
    URL,
    YourEmail,
    RequiredPassword,
    Checkbox,
    InlineCheckbox,
    Select,
    Names,
    Tags,
    Natural,
    Hidden,
    MultiSelect,
    Enum,
    Subscriptions,
    Quicklinks,
    RadioChoice,
    validate_name,
    NameNotValidError,
)
from moin.items import (
    BaseChangeForm,
    Item,
    NonExistent,
    NameNotUniqueError,
    MissingParentError,
    FieldNotUniqueError,
    get_itemtype_specific_tags,
    CreateItemForm,
    find_matches,
)
from moin.items.content import content_registry, conv_serialize
from moin.items.ticket import AdvancedSearchForm, render_comment_data
from moin import user
from moin.constants.keys import *  # noqa
from moin.constants.namespaces import *  # noqa
from moin.constants.itemtypes import ITEMTYPE_DEFAULT, ITEMTYPE_TICKET
from moin.constants.contenttypes import *  # noqa
from moin.constants.rights import SUPERUSER
from moin.constants.misc import FLASH_REPEAT
from moin.utils import crypto, rev_navigation, close_file, show_time, utcfromtimestamp
from moin.utils.crypto import make_uuid, hash_hexdigest
from moin.utils.interwiki import url_for_item, split_fqname, CompositeName
from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import html, docbook
from moin.search import SearchForm
from moin.search.analyzers import item_name_analyzer
from moin.signalling import item_displayed, item_modified
from moin.storage.middleware.protecting import AccessDenied, gen_fqnames
from moin.converters import default_registry as reg
from moin.storage.middleware.validation import validate_data
import moin.utils.mimetype as mime_type

from moin import log

logging = log.getLogger(__name__)


jfu_server_lock = threading.Lock()


@frontend.route("/+dispatch", methods=["GET"])
def dispatch():
    args = request.values.to_dict()
    endpoint = str(args.pop("endpoint"))
    # filter args given to url_for, so that no unneeded args end up in query string:
    args = {k: args[k] for k in args if app.url_map.is_endpoint_expecting(endpoint, k)}
    return redirect(url_for(endpoint, **args))


@frontend.route("/")
def show_root():
    item_name = app.cfg.root_mapping.get(NAMESPACE_DEFAULT, app.cfg.default_root)
    return redirect(url_for_item(item_name))


@frontend.route("/robots.txt")
def robots():
    return Response(
        """\
User-agent: *
Crawl-delay: 20
Disallow: /+convert/
Disallow: /+dom/
Disallow: /+download/
Disallow: /+modify/
Disallow: /+content/
Disallow: /+delete/
Disallow: /+ajaxdelete/
Disallow: /+ajaxdestroy/
Disallow: /+ajaxmodify/
Disallow: /+ajaxsubitems/
Disallow: /+destroy/
Disallow: /+create/
Disallow: /+rename/
Disallow: /+revert/
Disallow: /+index/
Disallow: /+jfu-server/
Disallow: /+sitemap/
Disallow: /+similar_names/
Disallow: /+quicklink/
Disallow: /+subscribe/
Disallow: /+forwardrefs/
Disallow: /+backrefs/
Disallow: /+wanteds/
Disallow: /+orphans/
Disallow: /+register
Disallow: /+recoverpass
Disallow: /+usersettings
Disallow: /+login
Disallow: /+logout
Disallow: /+bookmark
Disallow: /+diff/
Disallow: /+diffraw/
Disallow: /+search
Disallow: /+dispatch/
Disallow: /+admin/
Allow: /
""",
        mimetype="text/plain",
    )


@frontend.route("/all")
def global_views():
    """
    Provides a link to all the global views.
    """
    return render_template("all.html", title_name=_("Global Views"), fqname=CompositeName("all", NAME_EXACT, ""))


class LookupForm(Form):
    name = OptionalText.using(label="name")
    name_exact = OptionalText.using(label="name_exact")
    itemid = OptionalText.using(label="itemid")
    revid = OptionalText.using(label="revid")
    userid = OptionalText.using(label="userid")
    language = OptionalText.using(label="language")
    itemlinks = OptionalText.using(label="itemlinks")
    itemtransclusions = OptionalText.using(label="itemtransclusions")
    refs = OptionalText.using(label="refs")
    tags = Tags.using(optional=True).using(label="tags")
    history = InlineCheckbox.using(label=L_("search also in non-current revisions"))
    submit_label = L_("Lookup")


def analyze(analyzer, text):
    return [token.text for token in analyzer(text, mode="index")]


@frontend.route("/+lookup", methods=["GET", "POST"])
def lookup():
    """
    lookup is like search, but it only deals with specific fields that identify
    an item / revision. no query string parsing.

    for uuid fields, it performs a prefix search, so you can just give the
    first few digits. same is done for name_exact field.
    if you give a complete uuid or you do a lookup via the name field, it
    will use a simple search term.
    for one result, it directly redirects to the item/revision found.
    for none or multipe results, a result page is shown.

    usually this is used for links with a query string, like:
    /+lookup?itemid=123cba  (prefix match on itemid 123cba.......)
    /+lookup?revid=c0ddcda9a092499c92920cc4a9b11704  (full uuid simple term match)
    /+lookup?name_exact=FooBar/  (prefix match on name_exact FooBar/...)

    When giving history=1 it will use the all revisions index for lookup.
    """
    status = 200
    title_name = _("Lookup")
    # TAGS might be there multiple times, thus we need multi:
    lookup_form = LookupForm.from_flat(request.values.items(multi=True))
    valid = lookup_form.validate()
    if valid:
        history = bool(request.values.get("history"))
        idx_name = ALL_REVS if history else LATEST_REVS
        terms = []
        for key in [NAME, NAME_EXACT, ITEMID, REVID, USERID, LANGUAGE, TAGS, ITEMLINKS, ITEMTRANSCLUSIONS, "refs"]:
            value = lookup_form[key].value
            if value:
                if key in [ITEMID, REVID, USERID] and len(value) < crypto.UUID_LEN or key in [NAME_EXACT]:
                    term = Prefix(key, value)
                elif key == "refs":
                    term = Or([Term(ITEMLINKS, value), Term(ITEMTRANSCLUSIONS, value)])
                elif key == TAGS:
                    term = And([Term(TAGS, v.value) for v in lookup_form[key]])
                else:
                    term = Term(key, value)
                terms.append(term)
        if terms:
            LookupEntry = namedtuple("LookupEntry", "name revid wikiname")
            name = lookup_form[NAME].value
            name_exact = lookup_form[NAME_EXACT].value or ""
            terms.append(Term(WIKINAME, app.cfg.interwikiname))
            q = And(terms)
            with flaskg.storage.indexer.ix[idx_name].searcher() as searcher:
                flaskg.clock.start("lookup")
                results = searcher.search(q, limit=100)
                flaskg.clock.stop("lookup")
                lookup_results = []
                for result in results:
                    analyzer = item_name_analyzer()
                    lookup_results += [
                        LookupEntry(n, result[REVID], result[WIKINAME])
                        for n in result[NAME]
                        if not name or name.lower() in analyze(analyzer, n)
                        if n.startswith(name_exact)
                    ]

                if len(lookup_results) == 1:
                    result = lookup_results[0]
                    rev = result.revid if history else CURRENT
                    url = url_for(".show_item", item_name=result.name, rev=rev)
                    return redirect(url)
                else:
                    flaskg.clock.start("lookup render")
                    html = render_template(
                        "lookup.html", title_name=title_name, lookup_form=lookup_form, results=lookup_results
                    )
                    flaskg.clock.stop("lookup render")
                    if not lookup_results:
                        status = 404
                    return Response(html, status)
    html = render_template("lookup.html", title_name=title_name, lookup_form=lookup_form)
    return Response(html, status)


def _compute_item_transclusions(item_name):
    """Compute which items are transcluded into item <item_name>.

    :returns: a set of their item names.
    """
    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        # The search process should be as fast as possible so use
        # the indexer low-level documents instead of high-level Revisions.
        doc = searcher.document(**{NAME_EXACT: item_name})
        if not doc:
            return set()
        transcluded_names = set(doc[ITEMTRANSCLUSIONS])
        for item_name in transcluded_names.copy():
            transclusions = _compute_item_transclusions(item_name)
            transcluded_names.update(transclusions)
        return transcluded_names


def add_file_filters(_filter, filetypes):
    """
    Add various terms to the filter for the search query for the selected file types
    in the search options.

    :param _filter: the current filter
    :param filetypes: list of selected filetypes
    :returns: the required _filter for the search query
    """
    if filetypes and "all" not in filetypes:
        contenttypes = []
        files_filter = []
        if "markup" in filetypes:
            contenttypes.append(CONTENTTYPE_MARKUP)
        if "text" in filetypes:
            contenttypes.append(CONTENTTYPE_TEXT)
        if "image" in filetypes:
            contenttypes.append(CONTENTTYPE_IMAGE)
        if "audio" in filetypes:
            contenttypes.append(CONTENTTYPE_AUDIO)
        if "video" in filetypes:
            contenttypes.append(CONTENTTYPE_VIDEO)
        if "drawing" in filetypes:
            contenttypes.append(CONTENTTYPE_DRAWING)
        if "other" in filetypes:
            contenttypes.append(CONTENTTYPE_OTHER)
        for ctype in contenttypes:
            for itemtype in ctype:
                files_filter.append(Term("contenttype", itemtype))
        if "unknown" in filetypes:
            known_types = []
            for known in CONTENTTYPES_MAP.keys():
                known_types.append(Term("contenttype", known))
            unknown_types = Not(Or(known_types))
            if not files_filter:
                _filter.append(unknown_types)
                _filter = And(_filter)
                return _filter
            else:
                files_filter.append(unknown_types)
        files_filter = Or(files_filter)
        _filter.append(files_filter)
        _filter = And(_filter)
    return _filter


def add_facets(facets, time_sorting):
    """
    Adds various facets for the search features.

    :param facets: current facets
    :param time_sorting: defines the sorting order and can have one of the following 3 values :
                     1. default - default search, highest score first
                     2. old - sort old items first
                     3. new - sort new items first
                     4. name - sort by name
    :returns: required facets for the search query
    """
    if time_sorting == "new":
        facets.append(sorting.FieldFacet(MTIME, reverse=True))
    elif time_sorting == "old":
        facets.append(sorting.FieldFacet(MTIME, reverse=False))
    elif time_sorting == "name":
        facets.append(sorting.FieldFacet(NAME_SORT, reverse=False))
    return facets


@frontend.route("/+search/<itemname:item_name>", methods=["GET", "POST"])
@frontend.route("/+search", defaults=dict(item_name=""), methods=["GET", "POST"])
def search(item_name):
    """
    Perform a whoosh search of the index and display the matching items.

    The default search is across all namespaces in the index.

    The Jinja template formatting the output may also display data related to the
    search such as the whoosh query, filter (if any), hit counts, and additional
    suggested search terms.

    "Currently" there is no theme generating the '/+search/<itemname:item_name>' link
    within Item Views. To access, users must key the query link into the browsers URL. The
    query result is filtered limiting the output to the target item, target subitems
    and sub-subitems..., and transclusions within those items.
    Example URL: http://127.0.0.1:8080/+search/OtherTextItems?q=moin
    """
    search_form = SearchForm.from_flat(request.values)
    ajax = True if request.args.get("boolajax") else False
    valid = search_form.validate()
    time_sorting = False
    filetypes = []
    if ajax:
        query = request.args.get("q")
        history = request.args.get("history") == "true"
        time_sorting = request.args.get("time_sorting")
        if time_sorting == "default":
            time_sorting = False
        filetypes = request.args.get("filetypes")
        is_ticket = bool(request.args.get("is_ticket"))
        if filetypes:
            filetypes = filetypes.split(",")[:-1]  # To remove the extra '' at the end of the list
    else:
        query = search_form["q"].value
        history = bool(request.values.get("history"))

    best_match = False
    # we test for query in case this is a test run
    if query and query.startswith("\\"):
        best_match = True
        query = query[1:]

    if valid or ajax:
        # most fields in the schema use a StandardAnalyzer, it omits fairly frequently used words
        # this finds such words and reports to the user
        analyzer = StandardAnalyzer()
        omitted_words = [token.text for token in analyzer(query, removestops=False) if token.stopped]

        idx_name = ALL_REVS if history else LATEST_REVS

        if best_match:
            qp = flaskg.storage.query_parser([NAMES, NAMENGRAM], idx_name=idx_name)
        else:
            qp = flaskg.storage.query_parser(
                [NAMES, NAMENGRAM, TAGS, SUMMARY, SUMMARYNGRAM, CONTENT, CONTENTNGRAM, COMMENT], idx_name=idx_name
            )
        q = qp.parse(query)
        _filter = []
        _filter = add_file_filters(_filter, filetypes)
        if item_name:  # Only search this item and subitems
            prefix_name = item_name + "/"
            terms = [Term(NAME_EXACT, item_name), Prefix(NAME_EXACT, prefix_name)]

            show_transclusions = True
            if show_transclusions:
                # XXX Search subitems and all transcluded items (even recursively),
                # still looks like a hack. Imaging you have "foo" on main page and
                # "bar" on transcluded one. Then you search for "foo AND bar".
                # Such stuff would only work if we expand transcluded items
                # at indexing time (and we currently don't).
                with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
                    subq = Or([Term(NAME_EXACT, item_name), Prefix(NAME_EXACT, prefix_name)])
                    subq = And([subq, Every(ITEMTRANSCLUSIONS)])
                    flaskg.clock.start("search subitems with transclusions")
                    results = searcher.search(subq, limit=None)
                    flaskg.clock.stop("search subitems with transclusions")
                    transcluded_names = set()
                    for hit in results:
                        name = hit[NAME]
                        transclusions = _compute_item_transclusions(name)
                        transcluded_names.update(transclusions)
                # XXX Will whoosh cope with such a large filter query?
                terms.extend([Term(NAME_EXACT, tname) for tname in transcluded_names])
            _filter = Or(terms)

        with flaskg.storage.indexer.ix[idx_name].searcher() as searcher:
            # terms is set to retrieve list of terms which matched, in the searchtemplate, for highlight.
            facets = []
            facets = add_facets(facets, time_sorting)
            flaskg.clock.start("search")
            try:
                results = searcher.search(q, filter=_filter, limit=100, terms=True, sortedby=facets)
            # this may be an ajax transaction, search.js will handle a full page response
            except QueryError:
                flash(_("""QueryError: invalid search term: {search_term}""").format(search_term=q), "error")
                return render_template("search.html", query=query, medium_search_form=search_form, item_name=item_name)
            except TermNotFound:
                # name:'moin has bugs'
                flash(_("""TermNotFound: field is not indexed: {search_term}""").format(search_term=q), "error")
                return render_template("search.html", query=query, medium_search_form=search_form, item_name=item_name)
            flaskg.clock.stop("search")

            if best_match and results:
                return redirect(url_for_item(results[0][NAMES]))

            flaskg.clock.start("search render")
            if ajax:
                html = render_template(
                    "ajaxsearch.html",
                    results=results,
                    omitted_words=", ".join(omitted_words),
                    history=history,
                    is_ticket=is_ticket,
                    whoosh_query=q,
                    whoosh_filter=_filter,
                    flaskg=flaskg,
                )
            else:
                html = render_template(
                    "search.html",
                    results=results,
                    query=query,
                    medium_search_form=search_form,
                    item_name=item_name,
                    omitted_words=", ".join(omitted_words),
                    history=history,
                    whoosh_query=q,
                    whoosh_filter=_filter,
                    flaskg=flaskg,
                )
            flaskg.clock.stop("search render")
    else:
        html = render_template("search.html", query=query, medium_search_form=search_form, item_name=item_name)
    return html


def add_presenter(wrapped, view, add_trail=False, abort404=True):
    """
    Add new "presenter" views.

    Presenter views handle GET requests to locations like
    +{view}/+<rev>/<item_name> and +{view}/<item_name>, and always try to
    look up the item before processing.

    :param view: name of view
    :param add_trail: whether to call flaskg.user.add_trail
    :param abort404: whether to abort(404) for nonexistent items
    """

    @frontend.route(f"/+{view}/+<rev>/<itemname:item_name>")
    @frontend.route(f"/+{view}/<itemname:item_name>", defaults=dict(rev=CURRENT))
    @wraps(wrapped)
    def wrapper(item_name, rev):
        if add_trail:
            flaskg.user.add_trail(item_name)
        try:
            item = Item.create(item_name, rev_id=rev)
        except AccessDenied:
            abort(403)
        if abort404 and isinstance(item, NonExistent):
            abort(404, item_name)
        return wrapped(item)

    return wrapper


def presenter(view, add_trail=False, abort404=True):
    """
    Decorator factory to apply add_presenter().
    """
    return partial(add_presenter, view=view, add_trail=add_trail, abort404=abort404)


def flash_if_item_deleted(item_name, rev_id, itemrev):
    """
    Show flash info message if target item is deleted, show another message if revision is deleted.
    Return True if item is deleted or this revision is deleted.
    """
    if not rev_id == CURRENT:
        ret = False
        current_item = Item.create(item_name, rev_id=CURRENT)
        if TRASH in current_item.meta and current_item.meta[TRASH]:
            flash(_("This item is deleted."), "info")
            ret = True
        if TRASH in itemrev.meta and itemrev.meta[TRASH]:
            flash(_("This item revision is deleted."), "info")
            ret = True
        return ret
    elif TRASH in itemrev.meta and itemrev.meta[TRASH]:
        flash(_("This item is deleted."), "info")
        return True
    return False


# The first form accepts POST to allow modifying behavior like modify_item.
# The second form only accepts GET since modifying a historical revision is not allowed.
@frontend.route("/<itemname:item_name>", defaults=dict(rev=CURRENT), methods=["GET", "POST"])
@frontend.route("/+show/+<rev>/<itemname:item_name>", methods=["GET"])
def show_item(item_name, rev):
    fqname = split_fqname(item_name)
    item_displayed.send(app._get_current_object(), fqname=fqname)
    if not fqname.value and fqname.field == NAME_EXACT:
        fqname = fqname.get_root_fqname()
        return redirect(url_for_item(fqname))
    try:
        item = Item.create(item_name, rev_id=rev)
        flaskg.user.add_trail(item_name)
        item_is_deleted = flash_if_item_deleted(item_name, rev, item)
        result = item.do_show(rev, item_is_deleted=item_is_deleted)
    except AccessDenied:
        abort(403)
    except FieldNotUniqueError:
        revs = flaskg.storage.documents(**fqname.query)
        fq_names = []
        for rev in revs:
            fq_names.extend(rev.fqnames)
        return render_template(
            "link_list_no_item_panel.html",
            headline=_("Items with {field} {value}").format(field=fqname.field, value=fqname.value),
            fqname=fqname,
            fq_names=fq_names,
            item_is_deleted=item_is_deleted,
        )
    close_file(item.rev.data)
    return result


@frontend.route("/<itemname:item_name>/")  # note: unwanted trailing slash
@frontend.route("/+show/<itemname:item_name>")
def redirect_show_item(item_name):
    return redirect(url_for_item(item_name))


@presenter("dom", abort404=False)
def show_dom(item):
    if isinstance(item, NonExistent):
        status = 404
    else:
        status = 200
    content = render_template("dom.xml", data_xml=Markup(item.content._render_data_xml()))
    return Response(content, status, mimetype="text/xml")


# XXX this is just a temporary view to test the indexing converter
@frontend.route("/+indexable/+<rev>/<itemname:item_name>")
@frontend.route("/+indexable/<itemname:item_name>", defaults=dict(rev=CURRENT))
def indexable(item_name, rev):
    from moin.storage.middleware.indexing import convert_to_indexable

    try:
        item = flaskg.storage[item_name]
        rev = item[rev]
    except KeyError:
        abort(404, item_name)
    content = convert_to_indexable(rev.meta, rev.data, item_name)
    return Response(content, 200, mimetype="text/plain")


@presenter("highlight")
def highlight_item(item):
    rev_navigation_ids_dates = rev_navigation.prior_next_revs(request.view_args["rev"], item.fqname)
    item_is_deleted = flash_if_item_deleted(item.fqname.fullname, item.rev.meta[REVID], item)
    try:
        ret = render_template(
            "highlight.html",
            item=item,
            item_name=item.name,
            fqname=item.fqname,
            data_text=Markup(item.content._render_data_highlight()),
            rev=item.rev,
            rev_navigation_ids_dates=rev_navigation_ids_dates,
            meta=item._meta_info(),
            item_is_deleted=item_is_deleted,
        )
    except UnicodeDecodeError:
        return _crash(item, None, None)
    close_file(item.meta.revision.data)
    return ret


@presenter("meta", add_trail=True)
def show_item_meta(item):
    rev_navigation_ids_dates = rev_navigation.prior_next_revs(request.view_args["rev"], item.fqname)
    item_is_deleted = flash_if_item_deleted(item.fqname.fullname, item.rev.meta[REVID], item)
    ret = render_template(
        "meta.html",
        item=item,
        item_name=item.name,
        fqname=item.fqname,
        rev=item.rev,
        contenttype=item.contenttype,
        rev_navigation_ids_dates=rev_navigation_ids_dates,
        meta=item._meta_info(),
        item_is_deleted=item_is_deleted,
    )
    close_file(item.meta.revision.data)
    return ret


@frontend.route("/+content/+<rev>/<itemname:item_name>")
@frontend.route("/+content/<itemname:item_name>", defaults=dict(rev=CURRENT))
def content_item(item_name, rev):
    """same as show_item, but we only show the content"""
    fqname = split_fqname(item_name)
    item_displayed.send(app, fqname=fqname)
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    return render_template("content.html", item_name=item.name, data_rendered=Markup(item.content._render_data()))


@frontend.route("/+slideshow/<itemname:item_name>", defaults=dict(rev=CURRENT))
def slide_item(item_name, rev):
    """same as show_item, but we only show the content"""
    fqname = split_fqname(item_name)
    item_displayed.send(app, fqname=fqname)
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    data_rendered = Markup(item.content._render_data_slide())
    return render_template(
        "slideshow.html", item_name=item.name, full_name=fqname.fullname, data_rendered=data_rendered
    )


@presenter("get")
def get_item(item):
    return item.content.do_get()


@presenter("download")
def download_item(item):
    mimetype = request.values.get("mimetype")
    return item.content.do_get(force_attachment=True, mimetype=mimetype)


class ConvertForm(Form):
    new_type = Select.using(label=L_("New Content Type")).out_of(
        (
            ("text/x.moin.wiki;charset=utf-8", "MoinWiki"),
            ("text/x-markdown;charset=utf-8", "Markdown"),
            ("text/x-rst;charset=utf-8", "ReST"),
            ("application/x-xhtml-moin-page", "HTML"),
            ("application/docbook+xml;charset=utf-8", "DocBook"),
        )
    )
    comment = OptionalText.using(label=L_("Comment")).with_properties(placeholder=L_("Comment about your change"))
    submit_label = L_("OK")


@frontend.route("/+convert/<itemname:item_name>", methods=["GET", "POST"])
def convert_item(item_name):
    """
    Convert an item to a new or same content type.

    Converting an item to the same content type and then showing a diff
    is useful for hand-checking round trip conversions.

    The input may be any text-like item, the output is limited to
    the available converters.
    """
    try:
        item = Item.create(item_name, rev_id=CURRENT)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    form = ConvertForm.from_flat(request.form)
    if request.method in ["GET", "HEAD"]:
        return render_template(
            "convert.html", item=item, form=form, contenttype=item.contenttype, fqname=split_fqname(item_name)
        )

    item.rev.data.seek(0)
    content = item.rev.data.read()
    input_conv = reg.get(Type(item.contenttype), type_moin_document)
    dom = input_conv(content, item.contenttype)

    try:
        if not item.contenttype == form["new_type"].value:
            if not (
                item.contenttype in CONTENTTYPE_NO_EXPANSION and form["new_type"].value in CONTENTTYPE_NO_EXPANSION
            ):
                # expand DOM only when converting to dissimilar item types (moin and creole are similar)
                dom = item.content._expand_document(dom)

        conv_out = reg.get(type_moin_document, Type(form["new_type"].value))
        out = conv_out(dom)
    except Exception:
        logging.exception("Error converting item: %s", item.fqname)
        flash(L_("Item conversion failed"), "error")
        return redirect(url_for_item(**item.fqname.split))
    meta = dict(item.meta)
    if form["new_type"].value == "application/x-xhtml-moin-page":
        # serialize the html tree created by the html converter, and change content type
        out = conv_serialize(out, {html.namespace: ""})
        meta[CONTENTTYPE] = "text/html;charset=utf-8"
    elif form["new_type"].value == "application/docbook+xml;charset=utf-8":
        namespaces = {docbook.namespace: ""}
        out = conv_serialize(out, namespaces)
        meta[CONTENTTYPE] = form["new_type"].value
    else:
        meta[CONTENTTYPE] = form["new_type"].value
    out = out.encode(CHARSET)
    size, hash_name, hash_digest = hash_hexdigest(out)
    out = BytesIO(out)
    meta[hash_name] = hash_digest
    meta[SIZE] = size
    meta[PARENTID] = meta[REVID]
    meta[REVID] = make_uuid()
    meta[MTIME] = int(time.time())
    meta[REV_NUMBER] = meta.get(REV_NUMBER, 0) + 1
    meta[COMMENT] = form["comment"].value
    del meta["dataid"]
    out.seek(0)
    backend = flaskg.storage
    storage_item = backend.get_item(**item.fqname.query)
    newrev = storage_item.store_revision(
        meta,
        out,
        overwrite=False,
        action=str(ACTION_CONVERT),
        contenttype_current=Type(form["new_type"].value),
        contenttype_guessed=Type(form["new_type"].value),
        return_rev=True,
    )
    item_modified.send(
        app,
        fqname=meta["name"][0],
        action=ACTION_CONVERT,
        data=BytesIO(content),
        meta=item.meta,
        new_data=out,
        new_meta=newrev.meta,
    )
    flash(L_("Item converted successfully"), "info")
    return redirect(url_for_item(**item.fqname.split))


@frontend.route("/+modify/<itemname:item_name>", methods=["GET", "POST"])
def modify_item(item_name):
    """Modify the wiki item item_name.

    On GET, displays a form.
    On POST, saves the new page (unless there's an error in input).
    After successful POST, redirects to the page.
    """
    # XXX drawing applets don't send itemtype
    itemtype = request.values.get("itemtype", ITEMTYPE_DEFAULT)
    contenttype = request.values.get("contenttype")
    try:
        item = Item.create(item_name, itemtype=itemtype, contenttype=contenttype)
    except AccessDenied:
        abort(403)
    if not flaskg.user.may.write(item_name):
        abort(403)
    try:
        ret = item.do_modify()
    except ValueError as err:
        # user may have changed or deleted namespace, contenttype... causing meta data validation failure
        # or data unicode validation failed
        flash(str(err), "error")
        return redirect(url_for_item(item_name))
    close_file(item.rev.data)
    return ret


class TargetChangeForm(BaseChangeForm):
    target = RequiredText.using(label=L_("Target")).with_properties(
        placeholder=L_("The name of the target item"), autofocus=True
    )


class ValidRevert(Validator):
    """
    Validator for a valid revert form.
    """

    invalid_name_msg = ""

    def validate(self, element, state):
        """
        Check whether the names present in the previous meta are not taken by some other item.
        """
        try:
            validate_name(state["meta"], state["meta"].get(ITEMID))
            return True
        except NameNotValidError as e:
            self.invalid_name_msg = _(str(e))
            return self.note_error(element, state, "invalid_name_msg")


class RevertItemForm(BaseChangeForm):
    name = "revert_item"
    validators = [ValidRevert()]


class DeleteItemForm(BaseChangeForm):
    name = "delete_item"
    delete_subitems = Checkbox.using(label=L_("Delete all subitems listed below if checked:"))


class DestroyItemForm(BaseChangeForm):
    name = "destroy_item"
    destroy_subitems = Checkbox.using(label=L_("Destroy all subitems listed below if checked:"))


class RenameItemForm(TargetChangeForm):
    """
    Validator for a rename form.
    """

    def validate(self, element, state):
        """
        Element is a dict containing keys for 'name' and 'namespace'.
        state is current itemid.
        """
        try:
            validate_name(element, state)
            return True
        except NameNotValidError:
            return False


@frontend.route("/+create", methods=["POST"])
def create_item():
    """
    A user has corrected an invalid item name keyed into the +index > Create dialog or brower's URL.
    """
    form = CreateItemForm.from_flat(request.form)
    item_name = form["target"]
    return redirect(url_for_item(item_name))


@frontend.route("/+revert/+<rev>/<itemname:item_name>", methods=["GET", "POST"])
def revert_item(item_name, rev):
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDenied:
        abort(403)
    if not flaskg.user.may.write(item_name):
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    if request.method in ["GET", "HEAD"]:
        form = RevertItemForm.from_defaults()
    elif request.method == "POST":
        form = RevertItemForm.from_flat(request.form)
        state = dict(fqname=item.fqname, meta=dict(item.meta))
        if form.validate(state):
            item.revert(form["comment"])
            close_file(item.rev.data)
            name = CompositeName(item.fqname.namespace, NAME_EXACT, item.name)
            return redirect(url_for_item(name))
    ret = render_template(
        "revert.html",
        item=item,
        fqname=item.fqname,
        rev_id=rev,
        form=form,
        data_rendered=Markup(item.content._render_data()),
    )
    close_file(item.rev.data)
    return ret


@frontend.route("/+rename/<itemname:item_name>", methods=["GET", "POST"])
def rename_item(item_name):
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if not flaskg.user.may.write(item.fqname):
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    subitem_names = []
    if request.method in ["GET", "HEAD"]:
        form = RenameItemForm.from_defaults()
        form["target"] = ", ".join(item.names)
        subitems = item.get_subitem_revs()
        item_names = tuple(x + "/" for x in item.names)
        subitem_names = [y for x in subitems for y in x.meta[NAME] if y.startswith(item_names)]
    elif request.method == "POST":
        form = RenameItemForm.from_flat(request.form)
        target = form["target"]
        targets = [x.strip() for x in str(target).split(",") if x]
        alt_meta = {}
        alt_meta[NAME] = targets
        alt_meta[NAMESPACE] = item.meta[NAMESPACE]

        if form.validate(alt_meta, item.meta[ITEMID]):
            comment = form["comment"].value
            try:
                fqname = CompositeName(item.fqname.namespace, item.fqname.field, targets[0])
                item.rename(targets, comment)
                close_file(item.meta.revision.data)
                # the item was successfully renamed, show it with new name or first name if list
                return redirect(url_for_item(fqname))
            except NameNotUniqueError as e:
                flash(str(e), "error")
            except MissingParentError as e:
                flash(str(e), "error")
    ret = render_template(
        "rename.html",
        item=item,
        item_name=item_name,
        item_names=item.names,
        subitem_names=subitem_names,
        fqname=item.fqname,
        form=form,
        data_rendered=Markup(item.content._render_data()),
        len=len,
    )
    close_file(item.meta.revision.data)
    return ret


@frontend.route("/+delete/<itemname:item_name>", methods=["GET", "POST"])
def delete_item(item_name):
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if not flaskg.user.may.write(item.fqname):
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    subitem_names = []
    if request.method in ["GET", "HEAD"]:
        form = DeleteItemForm.from_defaults()
        subitems = list(item.get_subitem_revs())
        item_names = tuple(x + "/" for x in item.names)
        subitem_names = [y for x in subitems for y in x.meta[NAME] if y.startswith(item_names)]

        data_rendered = Markup(item.content._render_data())
        alias_names = set(item.names) - {item_name}
    elif request.method == "POST":
        form = DeleteItemForm.from_flat(request.form)
        if form.validate():
            comment = form["comment"].value
            do_subitems = form["delete_subitems"].value
            try:
                item.delete(comment, do_subitems=do_subitems)
            except AccessDenied:
                abort(403)
            close_file(item.meta.revision.data)
            return redirect(url_for_item(item_name))
    ret = render_template(
        "delete.html",
        item=item,
        item_name=item_name,
        alias_names=tuple(alias_names),
        subitem_names=subitem_names,
        fqname=split_fqname(item_name),
        form=form,
        data_rendered=data_rendered,
    )
    close_file(item.rev.data)
    return ret


@frontend.route("/+ajaxdelete/<itemname:item_name>", methods=["POST"])
@frontend.route("/+ajaxdelete", defaults=dict(item_name=""), methods=["POST"])
def ajaxdelete(item_name):
    return ajaxdestroy(item_name, req="delete")


@frontend.route("/+ajaxdestroy/<itemname:item_name>", methods=["POST"])
@frontend.route("/+ajaxdestroy", defaults=dict(item_name=""), methods=["POST"])
def ajaxdestroy(item_name, req="destroy"):
    """
    Handles both ajax delete and ajax destroy.

    Incoming item_name not currently used, contains parent name of items to be deleted/destroyed or ''.

    Jason response object includes these lists:
        - itemnames: list of item names and subnames successfully deleted/destroyed in url format
        - messages: formatted success/fail message for each item processed
    """
    args = request.values.to_dict()
    comment = args.get("comment")
    itemnames = args.get("itemnames")
    do_subitems = True if args.get("do_subitems") == "true" else False
    itemnames = json.loads(itemnames)
    response = {"itemnames": [], "messages": []}
    messages = []
    for itemname_url in itemnames:
        itemname = urllib.parse.unquote(itemname_url)  # itemname is url quoted str
        try:
            item = Item.create(itemname)
            if isinstance(item, NonExistent):
                # we should not try to destroy a nonexistent item,
                # user probably checked a subitem and checked do subitems
                response["messages"].append(_("Item '{bad_name}' does not exist.").format(bad_name=item.name))
                continue
            if req == "destroy":
                subitem_names = []
                if do_subitems:
                    subitems = item.get_subitem_revs()
                    # if subitem has alias of unselected sibling or ancester, it will be included
                    subitem_names = [x.meta.revision.names for x in subitems]
                messages, subitem_names = item.destroy(
                    comment=comment, destroy_item=True, subitem_names=subitem_names, ajax=True
                )
                log_destroy_action(item, subitem_names, comment)
            else:
                try:
                    messages, subitem_names = item.delete(comment, do_subitems=do_subitems, ajax=True)
                except AccessDenied:
                    # some deletes may have succeeded, one failed, there may be unprocessed items
                    msg = _("Access denied for a subitem of {bad_name}, check History for status.").format(
                        bad_name=itemname
                    )
                    response["messages"].append(msg)
            response["messages"] += messages
            response["itemnames"] += subitem_names + itemnames
        except AccessDenied:
            response["messages"].append(_("Access denied processing '{bad_name}'.").format(bad_name=itemname))
    response["itemnames"] = [url_for_item(x) for x in response["itemnames"]]
    return jsonify(response)


@frontend.route("/+ajaxmodify/<itemname:item_name>", methods=["POST"])
@frontend.route("/+ajaxmodify", methods=["POST"], defaults=dict(item_name=""))
def ajaxmodify(item_name):
    newitem = request.values.get("newitem")
    if not newitem:
        abort(404, item_name)
    if item_name:
        newitem = item_name + "/" + newitem
    return redirect(url_for_item(newitem))


@frontend.route("/+ajaxsubitems", methods=["POST"])
def ajaxsubitems():
    """
    Given a list of item names, return lists of alias names, subitem names,
    selected names (where user has auth to delete or destroy),
    and rejected names (where user has auth to read, but not delete or destroy).

    Note subitems are not checked for destroy auth.
    """
    item_names = request.values.getlist("item_names[]")
    action_auth = request.values.get("action_auth")
    all_alias_names = []
    all_subitem_names = []
    all_selected_names = []
    all_rejected_names = []
    for item_name in item_names:
        item_name = urllib.parse.unquote(item_name)
        try:
            item = Item.create(item_name, rev_id=CURRENT)
        except AccessDenied:
            abort(403)  # should never happen
        if isinstance(item, NonExistent):
            # user deletes item with alias, then tries to delete same item with other alias
            all_rejected_names.append(item_name)
            continue
        fqname = item.fqname
        if action_auth == "destroy":
            if not flaskg.user.may.destroy(fqname):
                # user can read this item, but not destroy
                all_rejected_names.append(item_name)
                continue
        else:
            if not flaskg.user.may.write(fqname):
                # user can read this item, but not delete
                all_rejected_names.append(item_name)
                continue
        alias_names = []
        subitems = list(item.get_subitem_revs())
        # TODO: add check for delete/destroy auth, add to rejected names,
        item_names = tuple(x + "/" for x in item.names)
        # subitems may have alias names pointing to sibling or parent of user selected items
        subitem_names = [y for x in subitems for y in x.meta[NAME]]
        if not [item.name] == item.names:
            alias_names = [x for x in item.names if not x == item.name]
        all_alias_names += alias_names
        all_subitem_names += subitem_names
        all_selected_names.append(item_name)
    all_subitem_names = set(all_subitem_names)
    response = {
        "subitem_names": list(all_subitem_names),
        "alias_names": all_alias_names,
        "selected_names": all_selected_names,
        "rejected_names": all_rejected_names,
    }
    return jsonify(response)


def log_destroy_action(item, subitem_names, comment, revision=None):
    """Document the destruction of an item or item revision."""
    destroy_info = [
        ("An item has been destroyed", ""),
        ("  Names", item.meta[NAME]),
        ("  Old Name", item.meta[NAME_OLD]),
        ("  Subitem Names", subitem_names),
        ("  Namespace", item.meta[NAMESPACE]),
        ("  Last Modified Time", format_datetime(utcfromtimestamp(item.meta[MTIME]))),
        ("  Last Modified By", item.meta[ADDRESS]),
        ("  Destroyed Time", format_datetime(utcfromtimestamp(time.time()))),
        ("  Destroyed By", flaskg.user.name),
        ("  Content Type", item.meta[CONTENTTYPE]),
        ("  Revision Number", item.meta[REV_NUMBER]),
        ("  Item Size", item.meta[SIZE]),
        ("  Comment", comment),
    ]
    if revision:
        destroy_info[0] = ("An item revision has been destroyed", item.meta[REV_NUMBER])
    elif subitem_names:
        destroy_info[0] = ("An item and all item subitems have been destroyed", "")
    for name, val in destroy_info:
        logging.info(f"{name}: {val}")


@frontend.route("/+destroy/+<rev>/<itemname:item_name>", methods=["GET", "POST"])
@frontend.route("/+destroy/<itemname:item_name>", methods=["GET", "POST"], defaults=dict(rev=None))
def destroy_item(item_name, rev):
    """
    If incoming item_name has alias names, then destroy processing is different than delete
    processing. With delete, the alias names survive intact. With destroy, the underlying data
    and meta files are removed so all alias names are destroyed.

    If the incoming target item `a` is deleted (Trash=True), then it is expected that all subitems
    of `a` are also deleted. Any subitems of `a` that are found using the metadata NAME_OLD
    links will be destroyed.

    If an item `a` with an alias `b` is deleted, then it is not possible to destroy `a` because
    `a` is not in the admin Trash list and there is no means of selecting `a`. However, any subitems
    of `a` that were deleted will appear in the admin Trash list and may be destroyed individually.

    :param item_name: item name or item ID if item is deleted
    :param rev: None if all revisions are to be destroyed or revision ID for specific revision
    :return: if GET rendered template, else POST will redirect to url to create item
    """
    if rev is None:
        # no revision given
        _rev = CURRENT  # for item creation
        destroy_item = True
    else:
        _rev = rev
        destroy_item = False
    try:
        item = Item.create(item_name, rev_id=_rev)
    except AccessDenied:
        abort(403)
    fqname = item.fqname
    if not flaskg.user.may.destroy(fqname):
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, fqname.fullname)
    item_is_deleted = flash_if_item_deleted(item_name, rev, item)
    subitem_names = []
    alias_names = []
    if rev is None and item_is_deleted:
        item_name = item.meta[NAME_OLD][0]
        subitems = item.get_subitem_revs()
        subitem_names = [y for x in subitems for y in x.meta[NAME_OLD] if y.startswith(item_name + "/")]
        if not [item_name] == item.meta[NAME_OLD]:
            alias_names = [x for x in item.meta[NAME_OLD] if not x == item_name]
    elif rev is None:
        subitems = item.get_subitem_revs()
        subitem_names = [y for x in subitems for y in x.meta[NAME] if y.startswith(item_name + "/")]
        if not [item.name] == item.names:
            alias_names = [x for x in item.names if not x == item.name]

    if request.method in ["GET", "HEAD"]:
        form = DestroyItemForm.from_defaults()
    elif request.method == "POST":
        form = DestroyItemForm.from_flat(request.form)
        if form.validate():
            comment = form["comment"].value
            do_subitems = form["destroy_subitems"].value
            if not do_subitems:
                subitem_names = []
            try:
                item.destroy(comment=comment, destroy_item=destroy_item, subitem_names=subitem_names)
            except AccessDenied:
                abort(403)
            log_destroy_action(item, subitem_names, comment, revision=rev)
            # show user item is deleted by showing "item does not exist, create it?" page
            return redirect(url_for_item(item_name))
    ret = render_template(
        "destroy.html",
        item=item,
        item_name=item_name,
        subitem_names=subitem_names,
        alias_names=alias_names,
        fqname=fqname,
        rev_id=rev,
        form=form,
        data_rendered=Markup(item.content._render_data()),
        item_is_deleted=item_is_deleted,
    )
    close_file(item.meta.revision.data)
    close_file(item.rev.data)
    return ret


@frontend.route("/+jfu-server/<itemname:item_name>", methods=["POST"])
@frontend.route("/+jfu-server", defaults=dict(item_name=""), methods=["POST"])
def jfu_server(item_name):
    """
    jquery-file-upload server component, returns a json response
    """
    msg = ""
    data_file = request.files.get("file_storage")
    base_file_name = os.path.basename(data_file.filename)
    file_name = secure_filename(base_file_name)
    if not file_name == base_file_name:
        msg = _("File Successfully uploaded and renamed from {bad_name} to {good_name}. ").format(
            bad_name=base_file_name, good_name=file_name
        )
    subitem_name = file_name
    data = data_file.stream
    mt = mime_type.MimeType(filename=file_name)
    contenttype = mt.content_type(charset="utf-8")
    small_meta = {CONTENTTYPE: contenttype}
    valid = validate_data(small_meta, data)
    if not valid:
        msg = _(
            "UnicodeDecodeError, upload failed, not a text file, nothing saved: '{file_name}'. "
            "Try changing the name."
        ).format(file_name=file_name)
        ret = make_response(
            jsonify(
                {
                    "name": subitem_name,
                    "files": [item_name],
                    "message": msg,
                    "class": "jfu-failed",
                    "contenttype": contenttype_to_class(contenttype),
                }
            ),
            200,
        )
        return ret

    if item_name:
        subitem_prefix = item_name + "/"
    else:
        subitem_prefix = ""
    item_name = subitem_prefix + subitem_name
    jfu_server_lock.acquire()
    try:
        item = Item.create(item_name)
        if not isinstance(item, NonExistent):
            msg += _("File Successfully uploaded, existing file overwritten: '{file_name}'.").format(
                file_name=file_name
            )
        revid, size = item.modify({"itemtype": ITEMTYPE_DEFAULT}, data, contenttype_guessed=contenttype)
        jfu_server_lock.release()
    except AccessDenied:
        # return 200 status with error message
        jfu_server_lock.release()
        msg = _("Permission denied, upload failed: '{file_name}'.").format(file_name=file_name)
        ret = make_response(
            jsonify(
                {
                    "name": subitem_name,
                    "files": [item_name],
                    "message": msg,
                    "class": "jfu-failed",
                    "contenttype": contenttype_to_class(contenttype),
                }
            ),
            200,
        )
        return ret

    data_file.close()
    item_modified.send(app, fqname=item.fqname, action=ACTION_SAVE, new_meta=item.meta)
    if not msg:
        msg = _("File Successfully uploaded: '{item_name}'.").format(item_name=item_name)
    ret = make_response(
        jsonify(
            name=subitem_name,
            files=[item_name],
            message=msg,
            size=size,
            url=url_for(".show_item", item_name=item_name),
            contenttype=contenttype_to_class(contenttype),
        ),
        200,
    )
    return ret


def contenttype_selects_gen():
    for g in content_registry.group_names:
        description = ", ".join([e.display_name for e in content_registry.groups[g]])
        yield g, None, description
    yield "Unknown Items", None, "Items of contenttype unknown to MoinMoin"


ContenttypeGroup = MultiSelect.of(Enum.out_of(contenttype_selects_gen())).using(optional=True)


class IndexForm(Form):
    contenttype = ContenttypeGroup
    submit_label = L_("Apply Filter")


@frontend.route("/+index/", defaults=dict(item_name=""), methods=["GET", "POST"])
@frontend.route("/+index/<itemname:item_name>", methods=["GET", "POST"])
def index(item_name):
    """
    Generate data for various index reports: global, sub-item, starts with character,
    or namespace. Identify missing items causing orphan sub-items.
    """

    def name_initial(files, uppercase=False, lowercase=False):
        """
        return a sorted list of first characters of subitem names,
        optionally all uppercased or lowercased.
        """
        initials = set()
        for item in files:
            initial = item.relname[0]
            if uppercase:
                initial = initial.upper()
            elif lowercase:
                initial = initial.lower()
            initials.add(initial)
        return sorted(list(initials))

    try:
        item = Item.create(item_name)  # when item_name='', it gives toplevel index
    except AccessDenied:
        abort(403)

    # request.args is a MultiDict instance, which degenerates into a normal
    # single-valued dict on most occasions (making the first value the *only*
    # value for a specific key) unless explicitly told to expose multiple
    # values, eg. calling items with multi=True. See Werkzeug documentation for
    # more.

    form = IndexForm.from_flat(request.args.items(multi=True))
    selected_groups = form["contenttype"].value
    startswith = request.values.get("startswith")
    dirs, files = item.get_index(startswith, selected_groups)
    dirs_fullname = [x.fullname for x in dirs]
    initials = request.values.get("initials")
    if initials:
        initials = initials.split(",")
    else:
        initials = name_initial(files, uppercase=True)
    fqname = item.fqname
    if fqname.value == NAMESPACE_ALL:
        fqname = CompositeName(NAMESPACE_ALL, NAME_EXACT, "")
    item_names = item_name.split("/")
    ns_len = len(item.meta["namespace"]) + 1 if item.meta["namespace"] else 0

    # detect orphan subitems and make a list of their missing parents
    used_dirs = set()
    for file_ in files:
        if file_.fullname in dirs_fullname:
            used_dirs.add(file_.fullname)
    all_dirs = {x.fullname for x in dirs}
    missing_dirs = all_dirs - used_dirs

    if selected_groups:
        # there will likely be false missing_dirs caused by filter
        missing = set()
        for m_dir in missing_dirs:
            query = And([Term(WIKINAME, app.cfg.interwikiname), (Term(NAME_EXACT, m_dir))])
            metas = tuple(flaskg.unprotected_storage.search_meta(query, idx_name=LATEST_REVS, limit=1))
            if not metas:
                missing.add(m_dir)
        missing_dirs = missing

    if item_name:
        what = ""
        if item.fqname.value == NAMESPACE_ALL:
            title = _("Global Index of All Namespaces")
        elif item.meta["namespace"]:
            what = _("Namespace '{name}' ").format(name=item.meta["namespace"])
            subitem = item_name[ns_len:]
            if subitem:
                what = what + _("subitems '{item_name}'").format(item_name=subitem)
            title = _("Index of {what}").format(what=what)
        else:
            title = _("Index of subitems '{item_name}'").format(item_name=item_name)
    else:
        title = _("Global Index")
    close_file(item.rev.data)

    return render_template(
        "index.html",
        title_name="Global Index",
        item_names=item_names,
        item_name=item_name,
        fqname=fqname,
        files=files,
        dirs=dirs,
        dirs_fullname=dirs_fullname,
        missing_dirs=missing_dirs,
        initials=initials,
        startswith=startswith,
        form=form,
        item=item,
        title=title,
        NAMESPACE_USERPROFILES=NAMESPACE_USERPROFILES,
        editors=editor_info_for_reports(),
        selected_groups=selected_groups,
        str=str,
        app=app,
    )


@frontend.route("/+mychanges")
def mychanges():
    """
    Returns the list of all revisions the current user has modified. The list is
    sorted in descending order by date-time and may be broken into pages
    based upon user or site settings for results-per-page.

    :returns: a page with all the items the current user has modified.
    """
    if flaskg.user.valid:
        results_per_page = flaskg.user.results_per_page
    else:
        flash(_("You must be logged in to see your changes."), "error")
        results_per_page = app.cfg.results_per_page
    page_num = request.values.get("page_num", 1)
    page_num = max(int(page_num), 1)

    query = And([Term(WIKINAME, app.cfg.interwikiname), Term(USERID, flaskg.user.itemid)])
    if results_per_page:
        len_revs = flaskg.storage.search_results_size(query, idx_name=ALL_REVS)
        metas = flaskg.storage.search_meta_page(
            query,
            idx_name=ALL_REVS,
            sortedby=[MTIME, REV_NUMBER],
            reverse=True,
            pagenum=page_num,
            pagelen=results_per_page,
        )
        pages = (len_revs + results_per_page - 1) // results_per_page
        if page_num > pages:
            # user has entered bad page_num in url
            page_num = pages
    else:
        pages = 1
        metas = flaskg.storage.search_meta(
            query, idx_name=ALL_REVS, sortedby=[MTIME, REV_NUMBER], reverse=True, limit=None
        )

    my_changes = []
    for meta in metas:
        entry = {}
        for key in (MTIME, SIZE, REV_NUMBER, REVID, CONTENTTYPE):
            entry[key] = meta[key]
        entry[COMMENT] = meta.get(COMMENT, "")
        entry[FQNAMES] = gen_fqnames(meta)
        entry[PARENTID] = meta.get(PARENTID, "")
        entry[TRASH] = meta.get(TRASH, False)
        entry[SUMMARY] = meta.get(SUMMARY, False)
        entry[NAME_OLD] = meta.get(NAME_OLD, False)
        my_changes.append(entry)

    return render_template(
        "mychanges.html",
        title_name=_("My Changes"),
        headline=_("My Changes"),
        my_changes=my_changes,
        page_num=page_num,
        pages=pages,
        url=request.url.split("?")[0],
    )


def shorten_item_id(name, length=7):
    """
    Shorten IDs starting with @itemid/ to specified length,
    """
    if name.startswith("@itemid/"):
        return name[8 : 8 + length]
    return name


@frontend.route("/+forwardrefs/<itemname:item_name>")
def forwardrefs(item_name):
    """
    Returns the list of all links or transclusions of item item_name

    :param item_name: the name of the current item
    :type item_name: unicode
    :returns: a page with all the items linked from this item
    """
    refs = _forwardrefs(item_name)
    return render_template(
        "link_list_item_panel.html",
        item_name=item_name,
        fqname=split_fqname(item_name),
        headline=_("Items that are referred by '{item_name}'").format(item_name=shorten_item_id(item_name)),
        fq_names=split_fqname_list(refs),
    )


def _forwardrefs(item_name):
    """
    Returns a list with all names of items that get referenced from item_name

    :param item_name: the name of the current item
    :type item_name: unicode
    :returns: the list of all items which are referenced from this item
    """
    fqname = split_fqname(item_name)
    q = fqname.query
    q[WIKINAME] = app.cfg.interwikiname
    rev = flaskg.storage.document(**q)
    if rev is None:
        refs = []
    else:
        refs = rev.meta.get(ITEMLINKS, []) + rev.meta.get(ITEMTRANSCLUSIONS, [])
    return set(refs)


@frontend.route("/+backrefs/<itemname:item_name>")
def backrefs(item_name):
    """
    Returns a list of all items that link or transclude item_name.

    :param item_name: the name of the current item
    :type item_name: unicode
    :returns: a page with all the items which link or transclude item_name
    """
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    refs_here = _backrefs(item_name)
    return render_template(
        "link_list_item_panel.html",
        item=item,
        item_name=item_name,
        fqname=split_fqname(item_name),
        headline=_("Items which refer to '{item_name}'").format(item_name=shorten_item_id(item_name)),
        fq_names=refs_here,
    )


def _backrefs(item_name):
    """
    Returns a list with all names of items which reference item_name.

    :param item_name: the name of the item transcluded or linked
    :type item_name: unicode
    :returns: the list of all items which ref fq_name
    """
    q = And(
        [Term(WIKINAME, app.cfg.interwikiname), Or([Term(ITEMTRANSCLUSIONS, item_name), Term(ITEMLINKS, item_name)])]
    )
    metas = flaskg.storage.search_meta(q)
    return {fqname for meta in metas for fqname in meta[FQNAMES]}


@frontend.route("/+history/<itemname:item_name>")
def history(item_name):
    fqname = split_fqname(item_name)
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)

    item_is_deleted = flash_if_item_deleted(item_name, CURRENT, item)
    page_num = request.values.get("page_num", 1)
    page_num = max(int(page_num), 1)
    bookmark_time = int(request.values.get("bookmark", 0))
    if flaskg.user.valid:
        results_per_page = flaskg.user.results_per_page
    else:
        results_per_page = app.cfg.results_per_page
    terms = [Term(WIKINAME, app.cfg.interwikiname)]
    terms.extend(Term(term, value) for term, value in fqname.query.items())
    if bookmark_time:
        terms.append(DateRange(MTIME, start=utcfromtimestamp(bookmark_time), end=None))
    query = And(terms)

    if results_per_page:
        len_revs = flaskg.storage.search_results_size(query, idx_name=ALL_REVS)
        metas = flaskg.storage.search_meta_page(
            query,
            idx_name=ALL_REVS,
            sortedby=[MTIME, REV_NUMBER],
            reverse=True,
            pagenum=page_num,
            pagelen=results_per_page,
        )
        pages = (len_revs + results_per_page - 1) // results_per_page
        if page_num > pages:
            page_num = pages
    else:
        pages = 1
        metas = flaskg.storage.search_meta(
            query, idx_name=ALL_REVS, sortedby=[MTIME, REV_NUMBER], reverse=True, limit=None
        )

    # get rid of the content value to save potentially big amounts of memory:
    history = []
    for meta in metas:
        entry = dict(meta)
        entry[FQNAMES] = gen_fqnames(meta)
        history.append(entry)
    close_file(item.rev.data)
    trash = item.meta["trash"] if "trash" in item.meta else False

    # avoid repeated IO to get user profile when same user edits this item multiple times
    editor_infos = {}  # userid: user_info
    for hist_meta in history:
        uid = hist_meta.get(USERID) or hist_meta.get(ADDRESS)
        if uid not in editor_infos:
            editor_infos[uid] = get_editor_info(hist_meta)
    flaskg.clock.start("renderrevs")
    ret = render_template(
        "history.html",
        fqname=fqname,
        item=item,
        item_name=item_name,
        history=history,
        page_num=page_num,
        pages=pages,
        editor_infos=editor_infos,
        bookmark_time=bookmark_time,
        NAME_EXACT=NAME_EXACT,
        len=len,
        trash=trash,
        item_is_deleted=item_is_deleted,
    )
    flaskg.clock.stop("renderrevs")
    close_file(item.rev.data)
    return ret


def editor_info_for_reports():
    """
    Return a {userid:(name, email or False), } dict extracted from the userprofiles namespace.

    This is useful for history and index reports that show the last editor's name and email address.
    It avoids multiple calls to whoosh for same userid.
    """
    query = And([Term(WIKINAME, app.cfg.interwikiname), (Term(NAMESPACE, NAMESPACE_USERPROFILES))])
    metas = flaskg.unprotected_storage.search_meta(query, idx_name=LATEST_REVS, limit=None)
    editors = {}
    for meta in metas:
        email = meta.get(EMAIL, False) if meta.get(MAILTO_AUTHOR, False) else False
        editors[meta[ITEMID]] = (meta[NAME][0], email)
    return editors


@frontend.route("/<namespace>/+history")
@frontend.route("/+history", defaults=dict(namespace=NAMESPACE_DEFAULT), methods=["GET"])
def global_history(namespace):
    all_revs = bool(request.values.get("all"))  # no UI help, user must add ?all=1 to url
    idx_name = ALL_REVS if all_revs else LATEST_REVS

    if flaskg.user.valid:
        results_per_page = flaskg.user.results_per_page
    else:
        results_per_page = app.cfg.results_per_page

    page_num = request.values.get("page_num", 1)
    page_num = max(int(page_num), 1)
    terms = [Term(WIKINAME, app.cfg.interwikiname)]
    fqname = CompositeName(NAMESPACE_ALL, NAME_EXACT, "")
    if namespace != NAMESPACE_ALL:
        terms.append(Term(NAMESPACE, namespace))
        fqname = split_fqname(namespace)
    else:
        terms.append(Not(Term(NAMESPACE, NAMESPACE_USERPROFILES)))
    bookmark_time = flaskg.user.bookmark
    if bookmark_time is not None:
        terms.append(DateRange(MTIME, start=utcfromtimestamp(bookmark_time), end=None))
    query = And(terms)

    if results_per_page:
        len_revs = flaskg.storage.search_results_size(query, idx_name=idx_name)
        metas = flaskg.storage.search_meta_page(
            query, idx_name=idx_name, sortedby=[MTIME], reverse=True, pagenum=page_num, pagelen=results_per_page
        )
        pages = (len_revs + results_per_page - 1) // results_per_page
        if page_num > pages:
            page_num = pages
    else:
        pages = 1
        metas = flaskg.storage.search_meta(query, idx_name=idx_name, sortedby=[MTIME], reverse=True, limit=None)
    # Group by date
    history = []
    day_history = namedtuple("day_history", ["day", "entries"])
    prev_date = "0000-00-00"
    dh = day_history(prev_date, [])  # dummy
    for meta in metas:
        meta[MTIME] = int(meta[MTIME].replace(tzinfo=timezone.utc).timestamp())
        meta[FQNAMES] = gen_fqnames(meta)
        rev_date = show_time.format_date(meta[MTIME])
        if rev_date == prev_date:
            dh.entries.append(meta)
        else:
            history.append(dh)
            dh = day_history(rev_date, [meta])
            prev_date = rev_date
    else:
        history.append(dh)
    del history[0]  # kill the dummy
    title_name = _("Global History")
    if namespace == NAMESPACE_ALL:
        title = _("Global History of All Namespaces")
    elif namespace:
        title = _("History of Namespace '{namespace}'").format(namespace=namespace)
    else:
        title = _("Global History")
    current_timestamp = int(time.time())
    return render_template(
        "global_history.html",
        title_name=title_name,
        history=history,
        current_timestamp=current_timestamp,
        bookmark_time=bookmark_time,
        fqname=fqname,
        title=title,
        int=int,
        page_num=page_num,
        pages=pages,
        url=request.url.split("?")[0],
    )


def _compute_item_sets(wanted=False):
    """
    compute sets of existing, linked, transcluded and no-revision item fqnames
    """
    linked = set()
    transcluded = set()
    existing = set()
    who_wants = {}
    query = And(
        [Term(WIKINAME, app.cfg.interwikiname), Not(Term(NAMESPACE, NAMESPACE_USERPROFILES)), Not(Term(TRASH, True))]
    )
    metas = flaskg.storage.search_meta(query, idx_name=LATEST_REVS, sortedby=[NAME], limit=None)
    if wanted:
        for meta in metas:
            existing |= set(meta[FQNAMES])
            linked.update(meta.get(ITEMLINKS, []))
            transcluded.update(meta.get(ITEMTRANSCLUSIONS, []))
            # who_wants needed by wanted_items, may add a few seconds of processing time for larger wikis
            for name in meta.get(ITEMLINKS, []):
                who_wants[name] = who_wants.get(name, []) + [meta[FQNAMES][0].fullname]
            for name in meta.get(ITEMTRANSCLUSIONS, []):
                who_wants[name] = who_wants.get(name, []) + [meta[FQNAMES][0].fullname]
    else:
        for meta in metas:
            existing |= set(meta[FQNAMES])
            linked.update(meta.get(ITEMLINKS, []))
            transcluded.update(meta.get(ITEMTRANSCLUSIONS, []))
    return existing, set(split_fqname_list(linked)), set(split_fqname_list(transcluded)), who_wants


def split_fqname_list(names):
    """
    Converts a list of names to a list of fqnames.
    """
    return [split_fqname(name) for name in names]


@frontend.route("/+wanteds")
def wanted_items():
    """
    Returns a list view of non-existing items that are linked to or
    transcluded by other items. Also returns the names of items
    having the links or transclusions.

    A second way of finding the items with the referred to links, is to
    use the backrefs functionality of the item in question. A UI backrefs
    link may not be present in all themes.
    """
    existing, linked, transcluded, who_wants = _compute_item_sets(wanted=True)
    referred = linked | transcluded
    wanteds = referred - existing
    title_name = _("Wanted Items")
    return render_template(
        "wanteds.html", headline=_("Wanted Items"), title_name=title_name, who_wants=who_wants, fq_names=wanteds
    )


@frontend.route("/+orphans")
def orphaned_items():
    """
    Return a list view of existing items not being linked or transcluded
    by any other item (which makes them sometimes not discoverable).
    """
    existing, linked, transcluded, who_wants = _compute_item_sets()
    referred = linked | transcluded
    orphans = existing - referred
    title_name = _("Orphaned Items")
    return render_template(
        "link_list_no_item_panel.html", title_name=title_name, headline=_("Orphaned Items"), fq_names=orphans
    )


@frontend.route("/+quicklink/<itemname:item_name>")
def quicklink_item(item_name):
    """Add/Remove the current wiki page to/from the user quicklinks"""
    u = flaskg.user
    msg = None
    if not u.valid:
        msg = _("You must login to use this action: {action}.").format(action="quicklink/quickunlink"), "error"
    elif not flaskg.user.is_quicklinked_to([item_name]):
        if not u.quicklink(item_name):
            msg = _("A quicklink to this page could not be added for you."), "error"
    else:
        if not u.quickunlink(item_name):
            msg = _("Your quicklink to this page could not be removed."), "error"
    if msg:
        flash(*msg)
    return redirect(url_for_item(item_name))


@frontend.route("/+subscribe/<itemname:item_name>")
def subscribe_item(item_name):
    """Add/Remove the current wiki item to/from the user's subscriptions"""
    u = flaskg.user
    msg = None
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    if not u.valid:
        msg = _("You must login to use this action: {action}.").format(action="subscribe/unsubscribe"), "error"
    elif not u.may.read(item_name):
        msg = _("You are not allowed to subscribe to an item you may not read."), "error"
    elif u.is_subscribed_to(item):
        # Try to unsubscribe
        if not u.unsubscribe(ITEMID, item.meta[ITEMID]):
            msg = (
                _("Can't remove the subscription! You are subscribed to this page, but not by itemid.")
                + " "
                + _("Please edit the subscription in your settings."),
                "error",
            )
    else:
        # Try to subscribe
        if not u.subscribe(ITEMID, item.meta[ITEMID]):
            msg = _("You could not get subscribed to this item."), "error"
    if msg:
        flash(*msg)
    return redirect(url_for_item(item_name))


class ValidRegistration(Validator):
    """Validator for a valid registration form"""

    passwords_mismatch_msg = L_("The passwords do not match.")

    def validate(self, element, state):
        if not (
            element["username"].valid
            and element["password1"].valid
            and element["password2"].valid
            and element["email"].valid
        ):
            return False
        if element["password1"].value != element["password2"].value:
            return self.note_error(element, state, "passwords_mismatch_msg")
        return True


class RegistrationForm(Form):
    """a simple user registration form"""

    name = "register"

    username = RequiredText.using(label=L_("Username")).with_properties(
        placeholder=L_("The login username you want to use"), autofocus=True
    )
    password1 = RequiredPassword.with_properties(placeholder=L_("The login password you want to use"))
    password2 = RequiredPassword.with_properties(placeholder=L_("Repeat the same password"))
    email = YourEmail
    submit_label = L_("Register")

    validators = [ValidRegistration()]


def _using_moin_auth():
    """Check if MoinAuth is being used for authentication.

    Only then users can register with moin or change their password via moin.
    """
    from moin.auth import MoinAuth

    for auth in app.cfg.auth:
        if isinstance(auth, MoinAuth):
            return True
    return False


@frontend.route("/+register", methods=["GET", "POST"])
def register():
    if app.cfg.registration_only_by_superuser and not getattr(flaskg.user.may, SUPERUSER)():
        # deny registration to bots
        abort(404)

    if not _using_moin_auth():
        return Response("No MoinAuth in auth list", 403)

    title_name = _("Register")
    template = "register.html"
    FormClass = RegistrationForm

    if request.method in ["GET", "HEAD"]:
        form = FormClass.from_defaults()
    elif request.method == "POST":
        form = FormClass.from_flat(request.form)
        if form.validate():
            user_kwargs = {
                "username": form["username"].value,
                "password": form["password1"].value,
                "email": form["email"].value,
            }
            if app.cfg.user_email_verification:
                user_kwargs["is_disabled"] = True
                user_kwargs["verify_email"] = True
            msg = user.create_user(**user_kwargs)
            if msg:
                flash(msg, "error")
            else:
                if app.cfg.user_email_verification:
                    u = user.User(auth_username=user_kwargs["username"])
                    is_ok, msg = u.mail_email_verification()
                    if is_ok:
                        flash(_("Account verification required, please see the email we sent to your address."), "info")
                    else:
                        flash(
                            _(
                                'An error occurred while sending the verification email: "{message}" '
                                "Please contact an administrator to activate your account."
                            ).format(message=msg),
                            "error",
                        )
                else:
                    flash(_("Account created, please log in now."), "info")
                return redirect(url_for(".show_root"))

    return render_template(template, title_name=title_name, form=form)


@frontend.route("/+verifyemail", methods=["GET"])
def verifyemail():
    u = token = None
    if "username" in request.values and "token" in request.values:
        u = user.User(auth_username=request.values["username"])
        token = request.values["token"]
    success = False
    if u and token and u.validate_recovery_token(token):
        unvalidated_email = u.profile[EMAIL_UNVALIDATED]
        if app.cfg.user_email_unique and user.search_users(**{EMAIL: unvalidated_email}):
            msg = _("This email is already in use.")
        else:
            if u.disabled:
                u.profile[DISABLED] = False
                msg = _("Your account has been activated, you can log in now.")
            else:
                msg = _("Your new email address has been confirmed.")
            u.profile[EMAIL] = unvalidated_email
            del u.profile[EMAIL_UNVALIDATED]
            del u.profile[RECOVERPASS_KEY]
            success = True
    else:
        msg = _("Your username and/or token is invalid!")
    if success:
        u.save()
        flash(msg, "info")
    else:
        flash(msg, "error")
    return redirect(url_for(".show_root"))


class ValidLostPassword(Validator):
    """Validator for a valid lost password form"""

    name_or_email_needed_msg = L_("Your user name or your email address is needed.")

    def validate(self, element, state):
        if not (
            element["username"].valid and element["username"].value or element["email"].valid and element["email"].value
        ):
            return self.note_error(element, state, "name_or_email_needed_msg")

        return True


class PasswordLostForm(Form):
    """a simple password lost form"""

    name = "lostpass"

    username = OptionalText.using(label=L_("Name")).with_properties(placeholder=L_("Your login name"))
    email = YourEmail.using(optional=True)
    submit_label = L_("Recover password")

    validators = [ValidLostPassword()]


@frontend.route("/+lostpass", methods=["GET", "POST"])
def lostpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    title_name = _("Lost Password")

    if not _using_moin_auth():
        return Response("No MoinAuth in auth list", 403)

    if request.method in ["GET", "HEAD"]:
        form = PasswordLostForm.from_defaults()
    elif request.method == "POST":
        form = PasswordLostForm.from_flat(request.form)
        if form.validate():
            u = None
            username = form["username"].value
            if username:
                u = user.User(auth_username=username)
            email = form["email"].value
            if form["email"].valid and email:
                users = user.search_users(email=email)
                u = users and user.User(users[0].meta[ITEMID])
            if u and u.valid:
                is_ok, msg = u.mail_password_recovery()
                if not is_ok:
                    flash(msg, "error")
            flash(_("If this account exists, you will be notified."), "info")
            return redirect(url_for(".show_root"))
    return render_template("lostpass.html", title_name=title_name, form=form)


class ValidPasswordRecovery(Validator):
    """Validator for a valid password recovery form"""

    passwords_mismatch_msg = L_("The passwords do not match.")
    password_problem_msg = L_("New password is unacceptable, could not get processed.")

    def validate(self, element, state):
        if element["password1"].value != element["password2"].value:
            return self.note_error(element, state, "passwords_mismatch_msg")

        password = element["password1"].value
        try:
            app.cfg.cache.pwd_context.hash(password)
        except (ValueError, TypeError):
            return self.note_error(element, state, "password_problem_msg")

        return True


class PasswordRecoveryForm(Form):
    """a simple password recovery form"""

    name = "recoverpass"

    username = RequiredText.using(label=L_("Name")).with_properties(placeholder=L_("Your login name"))
    token = RequiredText.using(label=L_("Recovery token")).with_properties(
        placeholder=L_("The recovery token that has been sent to you")
    )
    password1 = RequiredPassword.using(label=L_("New password")).with_properties(
        placeholder=L_("The login password you want to use")
    )
    password2 = RequiredPassword.using(label=L_("New password (repeat)")).with_properties(
        placeholder=L_("Repeat the same password")
    )
    submit_label = L_("Change password")

    validators = [ValidPasswordRecovery()]


@frontend.route("/+recoverpass", methods=["GET", "POST"])
def recoverpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    title_name = _("Recover Password")

    if not _using_moin_auth():
        return Response("No MoinAuth in auth list", 403)

    if request.method in ["GET", "HEAD"]:
        form = PasswordRecoveryForm.from_defaults()
        form.update(request.values)
    elif request.method == "POST":
        form = PasswordRecoveryForm.from_flat(request.form)
        if form.validate():
            u = user.User(auth_username=form["username"].value)
            if u and u.valid and u.apply_recovery_token(form["token"].value, form["password1"].value):
                flash(_("Your password has been changed, you can log in now."), "info")
            else:
                flash(_("Your token is invalid!"), "error")
            return redirect(url_for(".show_root"))
    return render_template("recoverpass.html", title_name=title_name, form=form)


class ValidLogin(Validator):
    """
    Login validator
    """

    moin_fail_msg = L_("Either your username or password was invalid.")

    def validate(self, element, state):
        # get the result from the other validators
        moin_valid = element["username"].valid and element["password"].valid

        # none of them was valid
        if not moin_valid:
            return False
        # got our user!
        if flaskg.user.valid:
            return True
        # no valid user -> show appropriate message
        else:
            if not moin_valid:
                return self.note_error(element, state, "moin_fail_msg")


class LoginForm(Form):
    """
    Login form
    """

    name = "login"

    username = RequiredText.using(label=L_("Username"), optional=False).with_properties(autofocus=True)
    password = RequiredPassword
    nexturl = Hidden.using(default="")
    # This field results in a login_submit field in the POST form, which is in
    # turn looked for by setup_user() in app.py as marker for login requests.
    submit = Hidden.using(default="1")
    submit_label = L_("Log in")

    validators = [ValidLogin()]


@frontend.route("/+login", methods=["GET", "POST"])
def login():
    title_name = _("Login")
    if request.method in ["GET", "HEAD"]:
        form = LoginForm.from_defaults()
        next_url = request.referrer or url_for(".show_root")
        if not next_url.startswith(request.host_url) or "/+" in next_url:
            next_url = url_for(".show_root")
        form["nexturl"].set(next_url)
        for authmethod in app.cfg.auth:
            hint = authmethod.login_hint()
            if hint:
                flash(hint, "info")
    elif request.method == "POST":
        form = LoginForm.from_flat(request.form)
        if form.validate():
            flash(_("You are logged in."), "info")
            nexturl = form["nexturl"]
            return redirect(str(nexturl))
        # this is executed when login fails due to bad ID or pw - app.py > def setup_user does successful logins
        for msg in flaskg._login_messages:
            # flash the error messages for failed login
            flash(msg, "error")
    return render_template("login.html", title_name=title_name, login_inputs=app.cfg.auth_login_inputs, form=form)


@frontend.route("/+logout")
def logout():
    flash(_("You are logged out."), "info")
    flaskg.user.logout_session()
    next_url = request.referrer or url_for(".show_root")
    if not next_url.startswith(request.host_url) or "/+" in next_url:
        next_url = url_for(".show_root")
    return redirect(next_url)


class ValidChangePass(Validator):
    """Validator for a valid password change"""

    passwords_mismatch_msg = L_("The passwords do not match.")
    current_password_wrong_msg = L_("The current password was wrong.")
    password_problem_msg = L_("New password is unacceptable, could not get processed.")

    def validate(self, element, state):
        password_not_accepted_msg = L_("New password not acceptable: ")

        if not (element["password_current"].valid and element["password1"].valid and element["password2"].valid):
            return False

        if not user.User(name=flaskg.user.name, password=element["password_current"].value).valid:
            return self.note_error(element, state, "current_password_wrong_msg")

        if element["password1"].value != element["password2"].value:
            return self.note_error(element, state, "passwords_mismatch_msg")

        password = element["password1"].value
        pw_checker = app.cfg.password_checker
        if pw_checker:
            pw_error = pw_checker(flaskg.user.name[0], password)
            if pw_error:
                return self.note_error(element, state, message=password_not_accepted_msg + pw_error)
        try:
            app.cfg.cache.pwd_context.hash(password)
        except (ValueError, TypeError):
            return self.note_error(element, state, "password_problem_msg")
        return True


class UserSettingsPasswordForm(Form):
    form_name = "usersettings_password"
    validators = [ValidChangePass()]

    password_current = RequiredPassword.using(label=L_("Current Password")).with_properties(
        placeholder=L_("Your current login password")
    )
    password1 = RequiredPassword.using(label=L_("New password")).with_properties(
        placeholder=L_("The login password you want to use")
    )
    password2 = RequiredPassword.using(label=L_("New password (repeat)")).with_properties(
        placeholder=L_("Repeat the same password")
    )
    submit_label = L_("Change password")


class UserSettingsNotificationForm(Form):
    form_name = "usersettings_notification"
    email = YourEmail
    submit_label = L_("Save")


class UserSettingsQuicklinksForm(Form):
    """
    No validation is performed as lots of things are valid, existing items, non-existing items,
    external links, mailto, external wiki links ...
    """

    form_name = "usersettings_quicklinks"
    quicklinks = Quicklinks
    submit_label = L_("Save")


class UserSettingsOptionsForm(Form):
    form_name = "usersettings_options"
    iso_8601 = Checkbox.using(label=L_("Always use ISO 8601 date-time format"))
    mailto_author = Checkbox.using(label=L_("Publish my email (not my wiki homepage) in author info"))
    edit_on_doubleclick = Checkbox.using(label=L_("Open editor on double click"))
    scroll_page_after_edit = Checkbox.using(label=L_("Scroll page after edit"))
    show_comments = Checkbox.using(label=L_("Show comment sections"))
    disabled = Checkbox.using(label=L_("Disable this account forever"))
    submit_label = L_("Save")


class ValidSubscriptions(Validator):
    """Validator for a subscriptions change"""

    def validate(self, element, state):
        # TODO: is additional validation for namespaces, itemids, names, or name prefixes needed?
        invalid_subscription_msg = L_("Invalid subscription syntax: ")
        invalid_keyword = L_("Invalid keyword: ")
        invalid_re_expression = L_("Invalid RE syntax: ")
        errors = []
        for subscription in element.value["subscriptions"]:
            try:
                keyword, value = subscription.split(":", 1)
            except ValueError:
                errors.append(invalid_subscription_msg + subscription)
                continue
            if keyword == ITEMID:
                continue
            if keyword not in (NAME, NAMEPREFIX, TAGS, NAMERE):
                errors.append(invalid_keyword + subscription)
                continue
            try:
                namespace, pattern = value.split(":", 1)
            except ValueError:
                errors.append(invalid_subscription_msg + subscription)
                continue
            if keyword == NAMERE:
                try:
                    pattern = re.compile(pattern, re.U)
                except re.error:
                    errors.append(invalid_re_expression + subscription)
                    continue
        if errors:
            return self.note_error(element, state, message=", ".join(errors))
        return True


class UserSettingsSubscriptionsForm(Form):
    form_name = "usersettings_subscriptions"
    subscriptions = Subscriptions
    submit_label = L_("Save")

    validators = [ValidSubscriptions()]


@frontend.route("/+usersettings", methods=["GET", "POST"])
def usersettings():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    title_name = _("User Settings")

    # werkzeug 1.0.0 dropped support for request.is_xhr,
    # was True if the request was triggered via a JavaScript XMLHttpRequest
    # TODO: maybe "is_xhr = request.method == 'POST'" would work
    is_xhr = request.accept_mimetypes.best in ("application/json", "text/javascript")

    class ValidUserSettingsPersonal(Validator):
        """Validator for settings personal change, name, display-name"""

        def validate(self, element, state):
            invalid_id_in_use_msg = L_("This name is already in use: ")
            invalid_character_msg = L_("The Display-Name contains invalid characters: ")
            invalid_character_message = L_("The Username contains invalid characters: ")
            errors = []
            if set(form["name"].value) != set(flaskg.user.name):
                new_names = set(form["name"].value) - set(flaskg.user.name)
                for name in new_names:
                    if user.search_users(**{NAME_EXACT: name}):
                        # duplicate name
                        errors.append(invalid_id_in_use_msg + name)
                if not user.normalizeName(name) == name:
                    errors.append(invalid_character_message + name)
            display_name = form[DISPLAY_NAME].value
            if display_name:
                if not user.normalizeName(display_name) == display_name:
                    errors.append(invalid_character_msg + display_name)
            if errors:
                return self.note_error(element, state, message=", ".join(errors))
            return True

    # these forms can't be global because we need app object, which is only available within a request:
    class UserSettingsPersonalForm(Form):
        form_name = "usersettings_personal"
        name = Names.using(label=L_("Usernames")).with_properties(placeholder=L_("The login usernames you want to use"))
        display_name = OptionalText.using(label=L_("Display-Name")).with_properties(
            placeholder=L_("Your display name (optional, rarely used)")
        )
        # _timezones_keys = sorted(Locale('en').time_zones.keys())
        _timezones_keys = [str(tz) for tz in pytz.common_timezones]
        timezone = Select.using(label=L_("Timezone")).out_of((e, e) for e in _timezones_keys)
        _supported_locales = app.extensions["babel"].instance.list_translations()
        locale = Select.using(label=L_("Locale")).out_of(
            [("auto", "---")] + [(str(locale), locale.display_name) for locale in _supported_locales], sort_by=1
        )
        submit_label = L_("Save")

        validators = [ValidUserSettingsPersonal()]

    class UserSettingsUIForm(Form):
        form_name = "usersettings_ui"
        theme_name = RadioChoice.using(label=L_("Theme name")).with_properties(
            choices=((str(t.identifier), t.name) for t in get_themes_list())
        )
        css_url = URL.using(label=L_("User CSS URL"), optional=True).with_properties(
            placeholder=L_("Give the URL of your custom CSS (optional)")
        )
        edit_rows = Natural.using(label=L_("Number rows in edit textarea")).with_properties(
            placeholder=L_("Editor textarea height (0=auto)")
        )
        results_per_page = Natural.using(label=L_("History results per page")).with_properties(
            placeholder=L_("Number of results per page (0=no paging)")
        )
        submit_label = L_("Save")

    form_classes = dict(
        personal=UserSettingsPersonalForm,
        password=UserSettingsPasswordForm,
        notification=UserSettingsNotificationForm,
        ui=UserSettingsUIForm,
        quicklinks=UserSettingsQuicklinksForm,
        options=UserSettingsOptionsForm,
        subscriptions=UserSettingsSubscriptionsForm,
    )
    forms = dict()

    if not flaskg.user.valid:
        return redirect(url_for(".login"))

    if request.method == "POST":
        part = request.form.get("part")
        if part not in form_classes:
            # the current part does not exist
            if is_xhr:
                # if the request is made via XHR, we return 404 Not Found
                abort(404)
            # otherwise we basically fall back to a normal GET request
            part = None

        if part:
            # create form object from request.form
            form = form_classes[part].from_flat(request.form)

            # save response to a dict as we can't use HTTP redirects or flash() for XHR requests
            response = dict(form=None, flash=[], redirect=None)

            if form.validate():
                # successfully modified everything
                success = True
                if part == "password":
                    flaskg.user.set_password(form["password1"].value)
                    flaskg.user.save()
                    response["flash"].append((_("Your password has been changed."), "info"))
                else:
                    if part == "notification":
                        if (
                            form["email"].value != flaskg.user.email
                            and user.search_users(**{EMAIL: form["email"].value})
                            and app.cfg.user_email_unique
                        ):
                            # duplicate email
                            response["flash"].append((_("This email is already in use"), "error"))
                            success = False
                    if success:
                        user_old_email = flaskg.user.email
                        d = dict(form.value)
                        for k, v in d.items():
                            if k == "locale" and v == "auto":
                                v = None  # None means "auto-detect language from http headers"
                            flaskg.user.profile[k] = v
                        if (
                            part == "notification"
                            and app.cfg.user_email_verification
                            and form["email"].value != user_old_email
                        ):
                            flaskg.user.profile[EMAIL] = user_old_email
                            flaskg.user.profile[EMAIL_UNVALIDATED] = form["email"].value
                            # send verification mail
                            is_ok, msg = flaskg.user.mail_email_verification()
                            if is_ok:
                                response["flash"].append(
                                    (
                                        _(
                                            "A confirmation email has been sent to your "
                                            "newly configured email address."
                                        ),
                                        "info",
                                    )
                                )
                                response["redirect"] = url_for(".show_root")
                            else:
                                # sending the verification email didn't work.
                                # delete the unvalidated email and alert the user.
                                del flaskg.user.profile[EMAIL_UNVALIDATED]
                                response["flash"].append(
                                    (
                                        _(
                                            "Your email address was not changed because sending the "
                                            "verification email failed. Please try again later."
                                        ),
                                        "error",
                                    )
                                )
                        else:
                            try:
                                flaskg.user.save()
                            except ValueError as err:
                                response["flash"].append((str(err), "error"))

            else:
                # validation failed
                response["flash"].append((_("Nothing saved."), "error"))

            if not response["flash"]:
                # if no flash message was added until here, we add a generic success message
                msg = _("Your changes have been saved.")
                response["flash"].append((msg, "info"))
                repeat_flash_msg(msg, "info")

            if response["redirect"] is not None or not is_xhr:
                # if we redirect or it is no XHR request, we just flash() the messages normally
                for f in response["flash"]:
                    flash(*f)

            if is_xhr:
                # if it is a XHR request, render the part from the usersettings_ajax.html template
                # and send the response encoded as an JSON object
                response["form"] = render_template("usersettings_ajax.html", part=part, form=form)
                return jsonify(**response)
            else:
                # if it is not a XHR request but there is an redirect pending, we use a normal HTTP redirect
                if response["redirect"] is not None:
                    return redirect(response["redirect"])

            # if the view did not return until here, we add the current form to the forms dict
            # and continue with rendering the normal template
            forms[part] = form

    # initialize all remaining forms
    for p, FormClass in form_classes.items():
        if p not in forms:
            forms[p] = FormClass.from_object(flaskg.user)

    return render_template("usersettings.html", title_name=title_name, form_objs=forms)


def repeat_flash_msg(msg, level):
    """
    Add a flash message to flask session. The message will be re-flashed by the next transaction.
    """
    if FLASH_REPEAT not in session:
        session[FLASH_REPEAT] = []
    session[FLASH_REPEAT].append((msg, level))


@frontend.route("/+bookmark")
def bookmark():
    """set bookmark (in time) for recent changes (or delete them)"""
    if flaskg.user.valid:
        timestamp = request.values.get("time")
        if timestamp is not None:
            if timestamp == "del":
                tm = None
            else:
                try:
                    tm = int(timestamp)
                except ValueError:
                    tm = int(time.time())
        else:
            tm = int(time.time())
        flaskg.user.bookmark = tm
    else:
        flash(_("You must log in to use bookmarks."), "error")
    return redirect(url_for(".global_history"))


def get_revs():
    """
    get 2 revids from values
    """
    rev1 = request.values.get("rev1")
    rev2 = request.values.get("rev2")
    if rev1 is None:
        # we require at least rev1
        abort(404)
    if rev2 is None:
        # rev2 is optional, use current rev if not given
        rev2 = CURRENT
    return rev1, rev2


@frontend.route("/+diffraw/<itemname:item_name>")
def diffraw(item_name):
    # TODO get_item and get_revision calls may raise an AccessDenied.
    #      If this happens for get_item, don't show the diff at all
    #      If it happens for get_revision, we may just want to skip that rev in the list
    # TODO verify if it does crash when the item does not exist
    try:
        item = flaskg.storage[item_name]
    except AccessDenied:
        abort(403)
    rev1, rev2 = get_revs()
    return _diff_raw(item, rev1, rev2)


@frontend.route("/+diff/<itemname:item_name>")
def diff(item_name):
    """
    Return an html fragment displaying an item diff and a rendered item revision.

    If call is made from a namespace Global History by a logged-in user who has
    set a bookmark, then the diff is made between the current revision and the
    revision just prior to the user's bookmark date-time or the oldest revision available.

    If the user is not logged-in or has no bookmark, then the call from Global history
    will pass the 2 most recent revision IDs to be compared. If a call is made from
    Item History or from a Diff display then the two revision IDs selected by the user
    will be processed.

    If the call is made from Item History, then there may be a difference in the
    display based upon whether the call is made based upon Item Name or
    Item ID. Calls based on Item IDs will include revisions prior to an item
    rename and revisions created by Item delete.
    """
    fqname = split_fqname(item_name)
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)

    offset = request.values.get("offset", 0)
    offset = max(int(offset), 0)
    bookmark_time = int(request.values.get("bookmark", 0))
    terms = [Term(WIKINAME, app.cfg.interwikiname)]
    terms.extend(Term(term, value) for term, value in fqname.query.items())
    query = And(terms)
    metas = flaskg.storage.search_meta(query, idx_name=ALL_REVS, sortedby=[MTIME, REV_NUMBER], reverse=True, limit=None)
    close_file(item.rev.data)
    item = flaskg.storage.get_item(**fqname.query)
    metas = [(int(meta[MTIME].replace(tzinfo=timezone.utc).timestamp()), meta[REVID], meta[ITEMID]) for meta in metas]
    if not metas:
        abort(404)
    # we do not do diffs across item IDs should an item be deleted and recreated with same name
    item_id = metas[0][2]
    rev_ids = [x[1] for x in metas if x[2] == item_id]
    rev_ids.reverse()
    if bookmark_time:
        # try to find the latest rev1 before user's bookmark <date-time>
        for mtime, revid, item_id in metas:
            if mtime <= int(bookmark_time):
                rev1 = revid
                break
        else:
            rev1 = revs[-1][1]  # if we didn't find a rev, we just take oldest rev we have
        rev2 = revs[0][1]  # and compare it with the current revision
    else:
        # otherwise we try get the 2 revids directly
        rev1 = request.values.get("rev1")
        rev2 = request.values.get("rev2")
        if rev1 not in rev_ids:
            if len(metas) > 1:
                rev1 = metas[1][1]  # take second newest rev
            else:
                rev1 = metas[0][1]  # we will compare rev to itself
                flash(_("There is only one revision eligible for diff."), "info")
        if rev2 not in rev_ids:
            rev2 = metas[0][1]  # the newest rev we have
    return _diff(item, rev1, rev2, fqname, rev_ids)


def _common_type(ct1, ct2):
    if ct1 == ct2:
        # easy, exactly the same content type, call do_diff for it
        commonmt = ct1
    else:
        major1 = ct1.split("/")[0]
        major2 = ct2.split("/")[0]
        if major1 == major2:
            # at least same major mimetype, use common base item class
            commonmt = major1 + "/"
        else:
            # nothing in common
            commonmt = ""
    return commonmt


def _crash(item, oldrev, newrev):
    """This is called from several places, need to handle passed message"""
    error_id = uuid.uuid4()
    logging.exception(f"An exception happened in _render_data (error_id = {error_id} ):")
    return render_template(
        "crash_view.html",
        server_time=time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        url=request.url,
        error_id=error_id,
        oldrev=oldrev,
        newrev=newrev,
        fqname=item.fqname,
        item=item,
    )


def _diff(item, revid1, revid2, fqname, rev_ids):
    """
    Return html fragment containing formatted diff and rendered item revision
    defined by revid2.
    """
    try:
        oldrev = item[revid1]
        newrev = item[revid2]
    except KeyError:
        abort(404)
    if oldrev.meta["mtime"] > newrev.meta["mtime"]:
        # within diff, always place oldest on left, newest on right
        oldrev, newrev = newrev, oldrev
        revid1, revid2 = revid2, revid1
    common_ct = _common_type(oldrev.meta[CONTENTTYPE], newrev.meta[CONTENTTYPE])

    try:
        item = Item.create(fqname.fullname, contenttype=common_ct, rev_id=newrev.revid)
    except AccessDenied:
        abort(403)

    # if there are many revisions, create rev_links dict with links to older and newer revisions on diff display
    rev_links = {}
    if len(rev_ids) > 2:
        rev1_idx = rev_ids.index(revid1)
        rev2_idx = rev_ids.index(revid2)
        if rev1_idx > 0:
            rev_links["r1_oldest"] = rev_ids[0]
            rev_links["r1_older"] = rev_ids[rev1_idx - 1]
        if rev2_idx > rev1_idx + 1:
            rev_links["r1_newer"] = rev_ids[rev1_idx + 1]
        end = len(rev_ids) - 1
        if rev2_idx < end:
            rev_links["r2_newer"] = rev_ids[rev2_idx + 1]
            rev_links["r2_newest"] = rev_ids[-1]
        if rev2_idx > rev1_idx + 1:
            rev_links["r2_older"] = rev_ids[rev2_idx - 1]
    if rev_links:
        rev_links["revid1"] = revid1
        rev_links["revid2"] = revid2

    try:
        diff_html = Markup(item.content._render_data_diff(oldrev, newrev, rev_links=rev_links, fqname=fqname))
    except Exception:
        return _crash(item, oldrev, newrev)

    return render_template("diff.html", item_name=item.name, fqname=item.fqname, diff_html=diff_html)


def _diff_raw(item, revid1, revid2):
    oldrev = item[revid1]
    newrev = item[revid2]
    if oldrev.meta["mtime"] > newrev.meta["mtime"]:
        oldrev, newrev = newrev, oldrev
        revid1, revid2 = revid2, revid1
    commonmt = _common_type(oldrev.meta[CONTENTTYPE], newrev.meta[CONTENTTYPE])

    try:
        item = Item.create(item.name, contenttype=commonmt, rev_id=newrev.revid)
    except AccessDenied:
        abort(403)
    return item.content._render_data_diff_raw(oldrev, newrev)


@frontend.route("/+similar_names/<itemname:item_name>")
def similar_names(item_name):
    """
    list similar item names
    """
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    fq_name = split_fqname(item_name)
    start, end, matches = find_matches(fq_name)
    keys = sorted(matches.keys())
    # TODO later we could add titles for the misc ranks:
    # 8 item_name
    # 4 "{0}/...".format(item_name)
    # 3 "{0}...{1}".format(start, end)
    # 1 "{0}...".format(start)
    # 2 "...{1}".format(end)
    fq_names = []
    for wanted_rank in [8, 4, 3, 1, 2]:
        for fqname in keys:
            rank = matches[fqname]
            if rank == wanted_rank:
                fq_names.append(fqname)
    return render_template(
        "link_list_item_panel.html",
        headline=_("Items with similar names to '{item_name}'").format(item_name=shorten_item_id(item_name)),
        item=item,
        item_name=item_name,  # XXX no item
        fqname=split_fqname(item_name),
        fq_names=fq_names,
    )


@frontend.route("/+sitemap/<itemname:item_name>")
def sitemap(item_name):
    """
    sitemap view shows item link structure relative to item_name.

    * If there are multiple links to same item, only first link to same item is processed.
    * Missing items are marked as missing in template rendering.
    * Links to items where current user lacks read authority are generated, but
       suppressed in template rendering.
    """
    fq_name = split_fqname(item_name)
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)

    backrefs, junk, junk2 = NestedItemListBuilder().recurse_build([fq_name], backrefs=True)
    del backrefs[0]  # don't show current item name as sole toplevel list item
    sitemap, no_read_auth, missing = NestedItemListBuilder().recurse_build([fq_name])
    del sitemap[0]  # don't show current item name as sole toplevel list item
    return render_template(
        "sitemap.html",
        item=item,
        item_name=item_name,
        backrefs=backrefs,
        sitemap=sitemap,
        fqname=fq_name,
        no_read_auth=no_read_auth,
        missing=missing,
    )


class NestedItemListBuilder:
    def __init__(self):
        self.children = set()
        self.no_read_auth = set()
        self.missing = set()

    def recurse_build(self, fq_names, backrefs=False):
        """
        Return a list of fqnames and lists containing more fqnames that represent a sitemap.
        """
        result = []
        for fq_name in fq_names:
            self.children.add(fq_name)
            result.append(fq_name)
            childs = self.childs(fq_name, backrefs=backrefs)
            if childs:
                childs, no_read_auth, missing = self.recurse_build(childs, backrefs=backrefs)
                result.append(childs)
        return result, self.no_read_auth, self.missing

    def childs(self, fq_name, backrefs=False):
        """
        Return a sorted list of fqnames that link-to or are linked-by fq_name)
        """
        try:
            item = flaskg.storage.get_item(**fq_name.query)
            meta = item.item.meta
            mayread = flaskg.storage.may_read_rev(meta)
        except (AccessDenied, KeyError):
            return []
        if item.itemid is None:
            self.missing.add(fq_name)
        if not mayread:
            # user lacks read permission to item already added to self.children
            # to save time we handle it later in template rendering
            self.no_read_auth.add(fq_name)
            return []
        if backrefs:
            itemlinks = _backrefs(fq_name.value)
        else:
            itemlinks = set(split_fqname_list(meta.get(ITEMLINKS, []) + meta.get(ITEMTRANSCLUSIONS, [])))
        # test for child not in self.children prevents loops when 2 or more items link to each other
        return sorted([child for child in itemlinks if child not in self.children])


@frontend.route("/+tags", defaults=dict(namespace=NAMESPACE_DEFAULT), methods=["GET"])
@frontend.route("/<namespace>/+tags")
def global_tags(namespace):
    """
    Show a list or tag cloud of tags in this wiki.

    If namespace == 'all' tags from all namespaces are shown.
    If namespace == '' tags from the default namespace are shown.
    If namespace == '<namespace>' tags from that namespace are shown.
    """
    title_name = _("Global Tags")
    if namespace == NAMESPACE_ALL:
        query = And([Term(WIKINAME, app.cfg.interwikiname), Term(HAS_TAG, True)])
        fqname = CompositeName(NAMESPACE_ALL, NAME_EXACT, "")
    else:
        query = And([Term(WIKINAME, app.cfg.interwikiname), Term(NAMESPACE, namespace), Term(HAS_TAG, True)])
        fqname = split_fqname(namespace)
    if namespace == NAMESPACE_DEFAULT:
        headline = _("Global Tags")
    elif namespace == NAMESPACE_ALL:
        headline = _("Global Tags in All Namespaces")
    else:
        headline = _("Tags in Namespace '{namespace}'").format(namespace=namespace)
    metas = flaskg.storage.search_meta(query, idx_name=LATEST_REVS, sortedby=[NAME], limit=None)
    tags_counts = {}
    for meta in metas:
        tags = meta.get(TAGS, [])
        logging.debug(f"name {meta[NAME]!r} rev {meta[REVID]} tags {tags!r}")
        for tag in tags:
            tags_counts[tag] = tags_counts.setdefault(tag, 0) + 1
    tags_counts = sorted(tags_counts.items())
    if tags_counts:
        # this is a simple linear scaling
        counts = [count for _tags, count in tags_counts]
        count_min = min(counts)
        count_max = max(counts)
        weight_max = 9.99
        if count_min == count_max:
            scale = weight_max / 2
        else:
            scale = weight_max / (count_max - count_min)

        def cls(count):
            # return the css class for this tag
            weight = scale * (count - count_min)
            return f"weight{int(weight)}"  # weight0, ..., weight9

        tags = [(cls(count), tag) for tag, count in tags_counts]
    else:
        tags = []
    return render_template("global_tags.html", headline=headline, title_name=title_name, fqname=fqname, tags=tags)


@frontend.route("/+tags/<itemname:tag>", defaults=dict(namespace=NAMESPACE_DEFAULT), methods=["GET"])
@frontend.route("/<namespace>/+tags/<itemname:tag>")
def tagged_items(tag, namespace):
    """
    show all items' names that have tag <tag> and belong to namespace <namespace>
    """
    terms = And([Term(WIKINAME, app.cfg.interwikiname), Term(TAGS, tag)])
    if namespace != NAMESPACE_ALL:
        terms = And([terms, Term(NAMESPACE, namespace)])
    query = And(terms)
    metas = flaskg.storage.search_meta(query, limit=None)
    fq_names = [gen_fqnames(meta) for meta in metas]
    fq_names = [fqn for sublist in fq_names for fqn in sublist]
    return render_template(
        "link_list_no_item_panel.html",
        headline=_("Items tagged with {tag}").format(tag=tag),
        item_name=tag,
        fq_names=fq_names,
    )


@frontend.route("/+template/<path:filename>")
def template(filename):
    """
    Serve a rendered template from <filename>

    used for (but not limited to) translation of javascript / css / html
    """
    content = render_template(filename)
    ct, enc = mimetypes.guess_type(filename)
    response = make_response((content, 200, {"content-type": ct or "text/plain;charset=utf-8"}))
    if ct in ["application/javascript", "text/css", "text/html"]:
        # this is assuming that:
        # * js / css / html templates rarely change (maybe just on sw updates)
        # * we are using templates for these to translate them, translations rarely change
        # * the rendered template output is just specific per user but does not change in time
        #   or by other circumstances
        cache_timeout = 24 * 3600  # 1 day
        is_public = False  # expanded template may be different for each user (translation)
    else:
        # safe defaults:
        cache_timeout = None
        is_public = False
    if cache_timeout is not None:
        # set some cache control headers, so browsers do not request this again and again:
        response.cache_control.public = is_public
        response.cache_control.max_age = cache_timeout
        response.expires = int(time.time() + cache_timeout)
    return response


@frontend.route("/+tickets", methods=["GET", "POST"])
def tickets():
    """
    Show a list of ticket items
    """
    if request.method == "POST":
        query = request.form["q"]
        status = request.form["status"]
    else:
        query = None
        status = "open"

    current_timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    idx_name = ALL_REVS
    qp = flaskg.storage.query_parser([TAGS, SUMMARY, CONTENT, ITEMID], idx_name=idx_name)
    term1 = [Term(ITEMTYPE, ITEMTYPE_TICKET)]
    term2 = []
    if query:
        term2.append(qp.parse(query))

    if status == "open":
        term1.append(Term(CLOSED, False))
    elif status == "closed":
        term1.append(Term(CLOSED, True))

    selected_tags = set(request.args.getlist("selected_tags"))
    term1.extend(Term(TAGS, tag) for tag in selected_tags)
    assigned_username = request.args.get(ASSIGNED_TO) or query
    user = [Term(NAME, assigned_username)]
    user.append(Term(CONTENTTYPE, CONTENTTYPE_USER))
    user = And(user)

    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        if assigned_username:
            selected_user = searcher.search(user, limit=None)
            if selected_user:
                assigned_to = selected_user[0][ITEMID]
                term2.append(Term(ASSIGNED_TO, assigned_to))
            elif not query:
                term2 = []
                term1 = []
        q = None
        # There are two cases when the user uses the search box in the ticket tracker and other
        # when user clicks on Assignee name in the ticket's table to view all tickets assigned to him
        # E.g. of link for second case is  +tickets?assigned_to=username .
        # For the first case, i.e. when using the search box, variable 'query' (i.e. what ever is searched)
        # should be present either in TAGS, SUMMARY, CONTENT, ITEMID 'or' ASSIGNED_TO 'and' should be
        # of given status (closed or open).
        # While in second case we have to get all the results having given status 'and'
        # Assigned_to = request.args.get(ASSIGNED_TO).
        # In first case we use 'and' while in second case we use 'or' while adding the assigned_to condition
        # to retrieve the results.
        if query:
            term2 = Or(term2)
            term1.extend([term2])
        else:
            term1.extend(term2)
        q = And(term1)
        results = searcher.search(q, limit=None)
        tags = get_itemtype_specific_tags(ITEMTYPE_TICKET)
        return render_template(
            "tickets.html",
            results=results,
            query=query,
            status=status,
            tags=tags,
            selected_tags=selected_tags,
            current_timestamp=current_timestamp,
        )


@frontend.route("/+tickets/query", methods=["GET", "POST"])
def ticket_search():
    """
    Suggest duplicate tickets while a new ticket is being created. Executed multiple times as user types/clicks.

    TODO: not useful as is, suggestions must match every word in ticket summary.
    Clicking radio buttons create updates but values seem to have no effect on results.
    Better suggestions may come from matching on tag values.
    """
    form = AdvancedSearchForm()
    suggested_tags = get_itemtype_specific_tags(ITEMTYPE_TICKET)
    results = []

    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        if request.method == "POST":
            effort = request.form.get("effort")
            difficulty = request.form.get("difficulty")
            severity = request.form.get("severity")
            priority = request.form.get("priority")
            tags = request.form.get("tags")
            assigned_to = request.form.get("assigned_to")
            author = request.form.get("author")
            term = [Term(ITEMTYPE, ITEMTYPE_TICKET)]
            if effort:
                term.append(Term(EFFORT, effort))
            if difficulty:
                term.append(Term(DIFFICULTY, difficulty))
            if severity:
                term.append(Term(SEVERITY, severity))
            if priority:
                term.append(Term(PRIORITY, priority))
            if tags:
                term.append(Term(TAGS, tags))
            if author:
                term.append(Term(USERID, author))
            if assigned_to:
                term.append(Term(ASSIGNED_TO, assigned_to))

            query = And(term)
            results = searcher.search(query, sortedby=NAME_EXACT, limit=None)

        return render_template(
            "ticket/advanced.html",
            search_form=form,
            ticket_results=results,
            suggested_tags=suggested_tags,
            timestamp=datetime.fromtimestamp,
            is_ticket=True,
        )


@frontend.route("/+comment", defaults=dict(item_name=""), methods=["POST"])
def comment(item_name):
    """
    Initiated by tickets.js when user clicks Save button adding a reply to a prior comment.

    An html fragment formatting a new comment is produced. It is inserted into the page via javascript.
    """
    itemid = request.form.get("refers_to")
    reply_to = request.form.get("reply_to")
    data = request.form.get("data")
    if data:
        current_timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        item_name = str(itemid) + "/" + "comment_" + str(current_timestamp)
        item = Item.create(item_name)
        item.modify(
            {},
            data=data,
            element="comment",
            contenttype_guessed="text/x.moin.wiki;charset=utf-8",
            refers_to=itemid,
            reply_to=reply_to,
            author=flaskg.user.name[0],
        )
        item = Item.create(item.name, rev_id=CURRENT)
        return render_template(
            "ticket/comment.html", comment=item, render_comment_data=render_comment_data, datetime=datetime
        )


@frontend.route("/+new", methods=["GET", "POST"])
def new():
    # TODO: Implement creation of blog entries and ticket items
    raise NotImplementedError


@frontend.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", path=request.path, item_name=e.description), 404
