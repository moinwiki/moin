# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2003-2013 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:AkashSinha
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2008 MoinMoin:FlorianKrupicka
# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2001 Richard Jones <richard@bizarsoftware.com.au>
# Copyright: 2001 Juergen Hermann <jh@web.de>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - frontend views

    This shows the usual things users see when using the wiki.
"""


import re
import difflib
import time
import uuid
import mimetypes
import json
from StringIO import StringIO
from datetime import datetime
from collections import namedtuple
from functools import wraps, partial

from flask import request, url_for, flash, Response, make_response, redirect, abort, jsonify
from flask import current_app as app
from flask import g as flaskg
from flask_babel import format_date
from flask_theme import get_themes_list

from flatland import Form, List
from flatland.validation import Validator

from jinja2 import Markup

import pytz
from babel import Locale

from whoosh import sorting
from whoosh.query import Term, Prefix, And, Or, DateRange, Every
from whoosh.query.qcore import QueryError
from whoosh.analysis import StandardAnalyzer
from whoosh import sorting

from MoinMoin.i18n import _, L_, N_
from MoinMoin.themes import render_template, contenttype_to_class
from MoinMoin.apps.frontend import frontend
from MoinMoin.forms import (OptionalText, RequiredText, URL, YourOpenID, YourEmail,
                            RequiredPassword, Checkbox, InlineCheckbox, Select, Names,
                            Tags, Natural, Hidden, MultiSelect, Enum, Subscriptions, Quicklinks,
                            validate_name, NameNotValidError)
from MoinMoin.items import (BaseChangeForm, TextChaizedForm, Item, NonExistent, NameNotUniqueError,
                            FieldNotUniqueError, get_itemtype_specific_tags, CreateItemForm)
from MoinMoin.items.content import content_registry, conv_serialize
from MoinMoin.items.ticket import AdvancedSearchForm, render_comment_data
from MoinMoin import user, util
from MoinMoin.constants.keys import *
from MoinMoin.constants.namespaces import *
from MoinMoin.constants.itemtypes import ITEMTYPE_DEFAULT, ITEMTYPE_TICKET, ITEMTYPE_USERPROFILE
from MoinMoin.constants.chartypes import CHARS_UPPER, CHARS_LOWER
from MoinMoin.constants.contenttypes import *
from MoinMoin.util import crypto, rev_navigation
from MoinMoin.util.crypto import make_uuid
from MoinMoin.util.interwiki import url_for_item, split_fqname, CompositeName
from MoinMoin.util.mime import Type, type_moin_document
from MoinMoin.util.tree import html, docbook
from MoinMoin.search import SearchForm
from MoinMoin.search.analyzers import item_name_analyzer
from MoinMoin.security.textcha import TextCha, TextChaizedForm
from MoinMoin.signalling import item_displayed, item_modified
from MoinMoin.storage.middleware.protecting import AccessDenied
from MoinMoin.converter import default_registry as reg
from MoinMoin.script.migration.moin19.import19 import hash_hexdigest

from MoinMoin import log
logging = log.getLogger(__name__)


@frontend.route('/+dispatch', methods=['GET', ])
def dispatch():
    args = request.values.to_dict()
    endpoint = str(args.pop('endpoint'))
    # filter args given to url_for, so that no unneeded args end up in query string:
    args = dict([(k, args[k]) for k in args
                 if app.url_map.is_endpoint_expecting(endpoint, k)])
    return redirect(url_for(endpoint, **args))


@frontend.route('/')
def show_root():
    item_name = app.cfg.root_mapping.get(NAMESPACE_DEFAULT, app.cfg.default_root)
    return redirect(url_for_item(item_name))


@frontend.route('/robots.txt')
def robots():
    return Response("""\
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
""", mimetype='text/plain')


@frontend.route('/favicon.ico')
def favicon():
    # although we tell that favicon.ico is at /static/logos/favicon.ico,
    # some browsers still request it from /favicon.ico...
    return app.send_static_file('logos/favicon.ico')


@frontend.route('/all')
def global_views():
    """
    Provides a link to all the global views.
    """
    return render_template('all.html',
                           title_name=_(u"Global Views"),
                           fqname=CompositeName(u'all', NAME_EXACT, u'')
                          )


class LookupForm(Form):
    name = OptionalText.using(label='name')
    name_exact = OptionalText.using(label='name_exact')
    itemid = OptionalText.using(label='itemid')
    revid = OptionalText.using(label='revid')
    userid = OptionalText.using(label='userid')
    language = OptionalText.using(label='language')
    itemlinks = OptionalText.using(label='itemlinks')
    itemtransclusions = OptionalText.using(label='itemtransclusions')
    refs = OptionalText.using(label='refs')
    tags = Tags.using(optional=True).using(label='tags')
    history = InlineCheckbox.using(label=L_('search also in non-current revisions'))
    submit_label = L_('Lookup')


def analyze(analyzer, text):
    return [token.text for token in analyzer(text, mode='index')]


@frontend.route('/+lookup', methods=['GET', 'POST'])
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
        history = bool(request.values.get('history'))
        idx_name = ALL_REVS if history else LATEST_REVS
        terms = []
        for key in [NAME, NAME_EXACT, ITEMID, REVID, USERID,
                    LANGUAGE,
                    TAGS,
                    ITEMLINKS, ITEMTRANSCLUSIONS, 'refs', ]:
            value = lookup_form[key].value
            if value:
                if key in [ITEMID, REVID, USERID, ] and len(value) < crypto.UUID_LEN or key in [NAME_EXACT]:
                    term = Prefix(key, value)
                elif key == 'refs':
                    term = Or([Term(ITEMLINKS, value), Term(ITEMTRANSCLUSIONS, value)])
                elif key == TAGS:
                    term = And([Term(TAGS, v.value) for v in lookup_form[key]])
                else:
                    term = Term(key, value)
                terms.append(term)
        if terms:
            LookupEntry = namedtuple('LookupEntry', 'name revid wikiname')
            name = lookup_form[NAME].value
            name_exact = lookup_form[NAME_EXACT].value or u''
            terms.append(Term(WIKINAME, app.cfg.interwikiname))
            q = And(terms)
            with flaskg.storage.indexer.ix[idx_name].searcher() as searcher:
                flaskg.clock.start('lookup')
                results = searcher.search(q, limit=100)
                flaskg.clock.stop('lookup')
                lookup_results = []
                for result in results:
                    analyzer = item_name_analyzer()
                    lookup_results += [LookupEntry(n, result[REVID], result[WIKINAME])
                                       for n in result[NAME]
                                       if not name or name.lower() in analyze(analyzer, n)
                                       if n.startswith(name_exact)]

                if len(lookup_results) == 1:
                    result = lookup_results[0]
                    rev = result.revid if history else CURRENT
                    url = url_for('.show_item', item_name=result.name, rev=rev)
                    return redirect(url)
                else:
                    flaskg.clock.start('lookup render')
                    html = render_template('lookup.html',
                                           title_name=title_name,
                                           lookup_form=lookup_form,
                                           results=lookup_results,
                    )
                    flaskg.clock.stop('lookup render')
                    if not lookup_results:
                        status = 404
                    return Response(html, status)
    html = render_template('lookup.html',
                           title_name=title_name,
                           lookup_form=lookup_form,
    )
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
    if filetypes:
        alltypes = "all" in filetypes
        contenttypes = []
        files_filter = []
        if alltypes or "markup" in filetypes:
            contenttypes.append(CONTENTTYPE_MARKUP)
        if alltypes or "text" in filetypes:
            contenttypes.append(CONTENTTYPE_TEXT)
        if alltypes or "image" in filetypes:
            contenttypes.append(CONTENTTYPE_IMAGE)
        if alltypes or "audio" in filetypes:
            contenttypes.append(CONTENTTYPE_AUDIO)
        if alltypes or "video" in filetypes:
            contenttypes.append(CONTENTTYPE_VIDEO)
        if alltypes or "drawing" in filetypes:
            contenttypes.append(CONTENTTYPE_DRAWING)
        if alltypes or "other" in filetypes:
            contenttypes.append(CONTENTTYPE_OTHER)
        for ctype in contenttypes:
            for itemtype in ctype:
                files_filter.append(Term("contenttype", itemtype))
        files_filter = Or(files_filter)
        _filter.append(files_filter)
        _filter = And(_filter)
    return _filter


def add_facets(facets, time_sorting):
    """
    Adds various facets for the search features.

    :param facets: current facets
    :param time_sorting: defines the sorting order and can have one of the following 3 values :
                     1. default - default search
                     2. old - sort old items first
                     3. new - sort new items first
    :returns: required facets for the search query
    """
    if time_sorting == "new":
        facets.append(sorting.FieldFacet("mtime", reverse=True))
    elif time_sorting == "old":
        facets.append(sorting.FieldFacet("mtime", reverse=False))
    return facets


@frontend.route('/+search/<itemname:item_name>', methods=['GET', 'POST'])
@frontend.route('/+search', defaults=dict(item_name=u''), methods=['GET', 'POST'])
def search(item_name):
    search_form = SearchForm.from_flat(request.values)
    ajax = True if request.args.get('boolajax') else False
    valid = search_form.validate()
    time_sorting = False
    filetypes = []
    if ajax:
        query = request.args.get('q')
        history = request.args.get('history') == "true"
        time_sorting = request.args.get('time_sorting')
        filetypes = request.args.get('filetypes')
        is_ticket = bool(request.args.get('is_ticket'))
        if filetypes:
            filetypes = filetypes.split(',')[:-1]  # To remove the extra u'' at the end of the list
    else:
        query = search_form['q'].value
        history = bool(request.values.get('history'))
    if valid or ajax:
        # most fields in the schema use a StandardAnalyzer, it omits fairly frequently used words
        # this finds such words and reports to the user
        analyzer = StandardAnalyzer()
        omitted_words = [token.text for token in analyzer(query, removestops=False) if token.stopped]

        idx_name = ALL_REVS if history else LATEST_REVS
        qp = flaskg.storage.query_parser([NAME_EXACT, NAME, SUMMARY, CONTENT, CONTENTNGRAM], idx_name=idx_name)
        q = qp.parse(query)

        _filter = []
        _filter = add_file_filters(_filter, filetypes)
        if item_name:  # Only search this item and subitems
            prefix_name = item_name + u'/'
            terms = [Term(NAME_EXACT, item_name), Prefix(NAME_EXACT, prefix_name), ]

            show_transclusions = True
            if show_transclusions:
                # XXX Search subitems and all transcluded items (even recursively),
                # still looks like a hack. Imaging you have "foo" on main page and
                # "bar" on transcluded one. Then you search for "foo AND bar".
                # Such stuff would only work if we expand transcluded items
                # at indexing time (and we currently don't).
                with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
                    subq = Or([Term(NAME_EXACT, item_name), Prefix(NAME_EXACT, prefix_name), ])
                    subq = And([subq, Every(ITEMTRANSCLUSIONS), ])
                    flaskg.clock.start('search subitems with transclusions')
                    results = searcher.search(subq, limit=None)
                    flaskg.clock.stop('search subitems with transclusions')
                    transcluded_names = set()
                    for hit in results:
                        name = hit[NAME]
                        transclusions = _compute_item_transclusions(name)
                        transcluded_names.update(transclusions)
                # XXX Will whoosh cope with such a large filter query?
                terms.extend([Term(NAME_EXACT, name) for name in transcluded_names])

            _filter = Or(terms)

        with flaskg.storage.indexer.ix[idx_name].searcher() as searcher:
            # terms is set to retrieve list of terms which matched, in the searchtemplate, for highlight.
            facets = []
            facets = add_facets(facets, time_sorting)
            flaskg.clock.start('search')
            try:
                results = searcher.search(q, filter=_filter, limit=100, terms=True, sortedby=facets)
            except QueryError:
                flash(_("""QueryError: invalid search term: %(search_term)s""", search_term=q), "error")
                return render_template('search.html',
                                       query=query,
                                       medium_search_form=search_form,
                                       item_name=item_name,
                                       )
            flaskg.clock.stop('search')
            flaskg.clock.start('search suggestions')
            name_suggestions = [word for word, score in results.key_terms(NAME, docs=20, numterms=10)]
            content_suggestions = [word for word, score in results.key_terms(CONTENT, docs=20, numterms=10)]
            flaskg.clock.stop('search suggestions')
            flaskg.clock.start('search render')

            lastword = query.split(' ')[-1]
            word_suggestions = []
            if len(lastword) > 2:
                corrector = searcher.corrector(CONTENT)
                word_suggestions = corrector.suggest(lastword, limit=3)
            if ajax:
                html = render_template('ajaxsearch.html',
                                       results=results,
                                       word_suggestions=u', '.join(word_suggestions),
                                       name_suggestions=u', '.join(name_suggestions),
                                       content_suggestions=u', '.join(content_suggestions),
                                       omitted_words=u', '.join(omitted_words),
                                       history=history,
                                       is_ticket=is_ticket,
                )
            else:
                html = render_template('search.html',
                                       results=results,
                                       name_suggestions=u', '.join(name_suggestions),
                                       content_suggestions=u', '.join(content_suggestions),
                                       query=query,
                                       medium_search_form=search_form,
                                       item_name=item_name,
                                       omitted_words=u', '.join(omitted_words),
                                       history=history,
                )
            flaskg.clock.stop('search render')
    else:
        html = render_template('search.html',
                               query=query,
                               medium_search_form=search_form,
                               item_name=item_name,
        )
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
    @frontend.route('/+{view}/+<rev>/<itemname:item_name>'.format(view=view))
    @frontend.route('/+{view}/<itemname:item_name>'.format(view=view), defaults=dict(rev=CURRENT))
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


# The first form accepts POST to allow modifying behavior like modify_item.
# The second form only accepts GET since modifying a historical revision is not allowed.
@frontend.route('/<itemname:item_name>', defaults=dict(rev=CURRENT), methods=['GET', 'POST'])
@frontend.route('/+show/+<rev>/<itemname:item_name>', methods=['GET'])
def show_item(item_name, rev):
    fqname = split_fqname(item_name)
    item_displayed.send(app._get_current_object(),
                        fqname=fqname)
    if not fqname.value and fqname.field == NAME_EXACT:
        fqname = fqname.get_root_fqname()
        return redirect(url_for_item(fqname))
    try:
        item = Item.create(item_name, rev_id=rev)
        flaskg.user.add_trail(item_name)
        result = item.do_show(rev)
    except AccessDenied:
        abort(403)
    except FieldNotUniqueError:
        revs = flaskg.storage.documents(**fqname.query)
        fq_names = []
        for rev in revs:
            fq_names.extend(rev.fqnames)
        return render_template("link_list_no_item_panel.html",
                               headline=_("Items with %(field)s %(value)s", field=fqname.field, value=fqname.value),
                               fqname=fqname,
                               fq_names=fq_names,
                               )
    if isinstance(item.rev.data, file):
        item.rev.data.close()
    return result


@frontend.route('/<itemname:item_name>/')  # note: unwanted trailing slash
@frontend.route('/+show/<itemname:item_name>')
def redirect_show_item(item_name):
    return redirect(url_for_item(item_name))


@presenter('dom', abort404=False)
def show_dom(item):
    if isinstance(item, NonExistent):
        status = 404
    else:
        status = 200
    content = render_template('dom.xml',
                              data_xml=Markup(item.content._render_data_xml()),
    )
    return Response(content, status, mimetype='text/xml')


# XXX this is just a temporary view to test the indexing converter
@frontend.route('/+indexable/+<rev>/<itemname:item_name>')
@frontend.route('/+indexable/<itemname:item_name>', defaults=dict(rev=CURRENT))
def indexable(item_name, rev):
    from MoinMoin.storage.middleware.indexing import convert_to_indexable
    try:
        item = flaskg.storage[item_name]
        rev = item[rev]
    except KeyError:
        abort(404, item_name)
    content = convert_to_indexable(rev.meta, rev.data, item_name)
    return Response(content, 200, mimetype='text/plain')


@presenter('highlight')
def highlight_item(item):
    rev_navigation_ids_dates = rev_navigation.prior_next_revs(request.view_args['rev'], item.fqname)
    try:
        ret = render_template('highlight.html',
                              item=item, item_name=item.name,
                              fqname=item.fqname,
                              data_text=Markup(item.content._render_data_highlight()),
                              rev=item.rev,
                              rev_navigation_ids_dates=rev_navigation_ids_dates,
                              meta=item._meta_info(),
        )
    except UnicodeDecodeError:
        return _crash(item, None, None)
    if isinstance(item.meta.revision.data, file):
        item.meta.revision.data.close()
    return ret


@presenter('meta', add_trail=True)
def show_item_meta(item):
    rev_navigation_ids_dates = rev_navigation.prior_next_revs(request.view_args['rev'], item.fqname)
    ret = render_template('meta.html',
                          item=item,
                          item_name=item.name,
                          fqname=item.fqname,
                          rev=item.rev,
                          contenttype=item.contenttype,
                          rev_navigation_ids_dates=rev_navigation_ids_dates,
                          meta=item._meta_info(),
    )
    if isinstance(item.meta.revision.data, file):
        item.meta.revision.data.close()
    return ret


@frontend.route('/+content/+<rev>/<itemname:item_name>')
@frontend.route('/+content/<itemname:item_name>', defaults=dict(rev=CURRENT))
def content_item(item_name, rev):
    """ same as show_item, but we only show the content """
    fqname = split_fqname(item_name)
    item_displayed.send(app, fqname=fqname)
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    return render_template('content.html',
                           item_name=item.name,
                           data_rendered=Markup(item.content._render_data()),
                           )


@presenter('get')
def get_item(item):
    return item.content.do_get()


@presenter('download')
def download_item(item):
    mimetype = request.values.get("mimetype")
    return item.content.do_get(force_attachment=True, mimetype=mimetype)


class ConvertForm(TextChaizedForm):
    new_type = Select.using(label=L_('New Content Type')).out_of((('text/x.moin.wiki;charset=utf-8', 'MoinWiki'),
                                                                  ('text/x-rst;charset=utf-8', 'ReST'),
                                                                  ('application/x-xhtml-moin-page', 'HTML'),
                                                                  ('application/docbook+xml;charset=utf-8', 'DocBook')))
    comment = OptionalText.using(label=L_('Comment')).with_properties(placeholder=L_("Comment about your change"), )
    submit_label = L_('OK')


@frontend.route('/+convert/<itemname:item_name>', methods=['GET', 'POST'])
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
    if request.method in ['GET', 'HEAD']:
        return render_template('convert.html',
                               item=item,
                               form=form,
                               contenttype=item.contenttype,
                               fqname=split_fqname(item_name),
                               )

    namespace = item.rev.meta.revision.namespace or 'default'
    revno = item.rev.revid
    item.rev.data.seek(0)
    content = item.rev.data.read()
    input_conv = reg.get(Type(item.contenttype), type_moin_document)
    dom = input_conv(content, item.contenttype)

    if item.contenttype in CONTENTTYPE_NO_EXPANSION and not form['new_type'].value in CONTENTTYPE_NO_EXPANSION:
        # expand macros, includes,... when converting from moin or creole to something other than moin or creole
        dom = item.content._expand_document(dom)

    conv_out = reg.get(type_moin_document, Type(form['new_type'].value))
    out = conv_out(dom)
    meta = dict(item.meta)
    if form['new_type'].value == 'application/x-xhtml-moin-page':
        # serialize the html tree created by the html converter, and change content type
        out = conv_serialize(out, {html.namespace: ''})
        meta[CONTENTTYPE] = 'text/html;charset=utf-8'
    elif form['new_type'].value == 'application/docbook+xml;charset=utf-8':
        namespaces = {docbook.namespace: '', }
        out = conv_serialize(out, namespaces)
        meta[CONTENTTYPE] = form['new_type'].value
    else:
        meta[CONTENTTYPE] = form['new_type'].value
    out = out.encode(CHARSET)
    size, hash_name, hash_digest = hash_hexdigest(out)
    out = StringIO(out)
    meta[hash_name] = hash_digest
    meta[SIZE] = size
    meta[REVID] = make_uuid()
    meta[MTIME] = int(time.time())
    meta[REV_NUMBER] = meta.get(REV_NUMBER, 0) + 1
    meta[COMMENT] = form['comment'].value
    del meta['dataid']
    out.seek(0)
    backend = flaskg.storage
    storage_item = backend.get_item(**item.fqname.query)
    newrev = storage_item.store_revision(meta, out, overwrite=False,
                                         action=unicode(ACTION_SAVE),
                                         contenttype_current=Type(form['new_type'].value),
                                         contenttype_guessed=Type(form['new_type'].value),
                                         return_rev=True,
                                         )
    item_modified.send(app, fqname=item.fqname, action=ACTION_SAVE)
    return redirect(url_for_item(**item.fqname.split))


@frontend.route('/+modify/<itemname:item_name>', methods=['GET', 'POST'])
def modify_item(item_name):
    """Modify the wiki item item_name.

    On GET, displays a form.
    On POST, saves the new page (unless there's an error in input).
    After successful POST, redirects to the page.
    """
    # XXX drawing applets don't send itemtype
    itemtype = request.values.get('itemtype', ITEMTYPE_DEFAULT)
    contenttype = request.values.get('contenttype')
    try:
        item = Item.create(item_name, itemtype=itemtype, contenttype=contenttype)
    except AccessDenied:
        abort(403)
    if not flaskg.user.may.write(item_name):
        abort(403)
    try:
        ret = item.do_modify()
    except UnicodeDecodeError:
        return _crash(item, None, None)
    except ValueError:
        # user may have changed or deleted namespace, contenttype, or strict data validation failed in indexing.py
        flash(_("""Error: nothing changed. Meta data validation failed."""), "error")
        return redirect(url_for_item(item_name))
    try:
        if isinstance(item.meta.revision.data, file):
            item.meta.revision.data.close()
    except AttributeError:
        pass
    return ret


class TargetChangeForm(BaseChangeForm):
    target = RequiredText.using(label=L_('Target')).with_properties(placeholder=L_("The name of the target item"), autofocus=True)


class ValidRevert(Validator):
    """
    Validator for a valid revert form.
    """
    invalid_name_msg = ''

    def validate(self, element, state):
        """
        Check whether the names present in the previous meta are not taken by some other item.
        """
        try:
            validate_name(state['meta'], state['meta'].get(ITEMID))
            return True
        except NameNotValidError as e:
            self.invalid_name_msg = _(e)
            return self.note_error(element, state, 'invalid_name_msg')


class RevertItemForm(BaseChangeForm):
    name = 'revert_item'
    validators = [ValidRevert()]


class DeleteItemForm(BaseChangeForm):
    name = 'delete_item'


class DestroyItemForm(BaseChangeForm):
    name = 'destroy_item'


class RenameItemForm(TargetChangeForm):
    name = 'rename_item'


@frontend.route('/+create', methods=['POST'])
def create_item():
    """
    A user has corrected an invalid item name keyed into the +index > Create dialog or brower's URL.
    """
    form = CreateItemForm.from_flat(request.form)
    item_name = form['target']
    return redirect(url_for_item(item_name))


@frontend.route('/+revert/+<rev>/<itemname:item_name>', methods=['GET', 'POST'])
def revert_item(item_name, rev):
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDenied:
        abort(403)
    if not flaskg.user.may.write(item_name):
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    if request.method in ['GET', 'HEAD']:
        form = RevertItemForm.from_defaults()
        TextCha(form).amend_form()
    elif request.method == 'POST':
        form = RevertItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        state = dict(fqname=item.fqname, meta=dict(item.meta))
        if form.validate(state):
            item.revert(form['comment'])
            if isinstance(item.meta.revision.data, file):
                item.meta.revision.data.close()
            return redirect(url_for_item(item_name))
    ret = render_template('revert.html',
                          item=item,
                          fqname=item.fqname,
                          rev_id=rev,
                          form=form,
                          data_rendered=Markup(item.content._render_data()),
    )
    if isinstance(item.meta.revision.data, file):
        item.meta.revision.data.close()
    return ret


@frontend.route('/+rename/<itemname:item_name>', methods=['GET', 'POST'])
def rename_item(item_name):
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if not flaskg.user.may.write(item.fqname):
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    if request.method in ['GET', 'HEAD']:
        form = RenameItemForm.from_defaults()
        TextCha(form).amend_form()
        form['target'] = item.name
    elif request.method == 'POST':
        form = RenameItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        if form.validate():
            target = form['target'].value
            comment = form['comment'].value
            namespaces = [namespace.rstrip('/') for namespace, _ in app.cfg.namespace_mapping]
            namespaces = namespaces + NAMESPACES_IDENTIFIER
            if target.split('/', 1)[0] in namespaces:
                msg = L_("Item name segment (%(invalid_name)s) must not match existing namespaces.", invalid_name=target.split('/', 1)[0])
                flash(msg, "error")
            else:
                try:
                    fqname = CompositeName(item.fqname.namespace, item.fqname.field, target)
                    item.rename(target, comment)
                    if isinstance(item.meta.revision.data, file):
                        item.meta.revision.data.close()
                    # the item was successfully renamed, show it with new name
                    return redirect(url_for_item(fqname))
                except NameNotUniqueError as e:
                    flash(str(e), "error")
    ret = render_template('rename.html',
                          item=item, item_name=item_name,
                          fqname=item.fqname,
                          form=form,
    )
    if isinstance(item.meta.revision.data, file):
        item.meta.revision.data.close()
    return ret


@frontend.route('/+delete/<itemname:item_name>', methods=['GET', 'POST'])
def delete_item(item_name):
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if not flaskg.user.may.write(item.fqname):
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    if request.method in ['GET', 'HEAD']:
        form = DeleteItemForm.from_defaults()
        TextCha(form).amend_form()
    elif request.method == 'POST':
        form = DeleteItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        if form.validate():
            comment = form['comment'].value
            try:
                item.delete(comment)
            except AccessDenied:
                abort(403)
            return redirect(url_for_item(item_name))
    return render_template('delete.html',
                           item=item, item_name=item_name,
                           fqname=split_fqname(item_name),
                           form=form,
    )


@frontend.route('/+ajaxdelete/<itemname:item_name>', methods=['POST'])
@frontend.route('/+ajaxdelete', defaults=dict(item_name=''), methods=['POST'])
def ajaxdelete(item_name):
    if request.method == 'POST':
        args = request.values.to_dict()
        comment = args.get("comment")
        itemnames = args.get("itemnames")
        itemnames = json.loads(itemnames)
        if item_name:
            subitem_prefix = item_name + u'/'
        else:
            subitem_prefix = u''
        response = {"itemnames": [], "status": []}
        for itemname in itemnames:
            response["itemnames"].append(itemname)
            itemname = subitem_prefix + itemname
            try:
                item = Item.create(itemname)
                item.delete(comment)
                response["status"].append(True)
            except AccessDenied:
                response["status"].append(False)

    return jsonify(response)


@frontend.route('/+ajaxdestroy/<itemname:item_name>', methods=['POST'])
@frontend.route('/+ajaxdestroy', defaults=dict(item_name=''), methods=['POST'])
def ajaxdestroy(item_name):
    if request.method == 'POST':
        args = request.values.to_dict()
        comment = args.get("comment")
        itemnames = args.get("itemnames")
        itemnames = json.loads(itemnames)
        if item_name:
            subitem_prefix = item_name + u'/'
        else:
            subitem_prefix = u''
        response = {"itemnames": [], "status": []}
        for itemname in itemnames:
            response["itemnames"].append(itemname)
            itemname = subitem_prefix + itemname
            try:
                item = Item.create(itemname)
                item.destroy(comment=comment, destroy_item=True)
                response["status"].append(True)
            except AccessDenied:
                response["status"].append(False)

    return jsonify(response)


@frontend.route('/+ajaxmodify/<itemname:item_name>', methods=['POST'])
@frontend.route('/+ajaxmodify', methods=['POST'], defaults=dict(item_name=''))
def ajaxmodify(item_name):
    newitem = request.values.get("newitem")
    if not newitem:
        abort(404, item_name)
    if item_name:
        newitem = item_name + u'/' + newitem
    return redirect(url_for_item(newitem))


@frontend.route('/+destroy/+<rev>/<itemname:item_name>', methods=['GET', 'POST'])
@frontend.route('/+destroy/<itemname:item_name>', methods=['GET', 'POST'], defaults=dict(rev=None))
def destroy_item(item_name, rev):
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
    if request.method in ['GET', 'HEAD']:
        form = DestroyItemForm.from_defaults()
        TextCha(form).amend_form()
    elif request.method == 'POST':
        form = DestroyItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        if form.validate():
            comment = form['comment'].value
            try:
                item.destroy(comment=comment, destroy_item=destroy_item)
            except AccessDenied:
                abort(403)
            # show user item is deleted by showing "item does not exist, create it?" page
            return redirect(url_for_item(fqname.fullname))
    if isinstance(item.meta.revision.data, file):
        item.meta.revision.data.close()
    ret = render_template('destroy.html',
                          item=item, item_name=item_name,
                          fqname=fqname,
                          rev_id=rev,
                          form=form,
    )
    if isinstance(item.rev.data, file):
        item.rev.data.close()
    return ret


import threading
jfu_server_lock = threading.Lock()


@frontend.route('/+jfu-server/<itemname:item_name>', methods=['POST'])
@frontend.route('/+jfu-server', defaults=dict(item_name=''), methods=['POST'])
def jfu_server(item_name):
    """jquery-file-upload server component
    """
    data_file = request.files.get('data_file')
    subitem_name = data_file.filename
    contenttype = data_file.content_type  # guess by browser, based on file name
    data = data_file.stream
    if item_name:
        subitem_prefix = item_name + u'/'
    else:
        subitem_prefix = u''
    item_name = subitem_prefix + subitem_name
    jfu_server_lock.acquire()
    try:
        item = Item.create(item_name)
        revid, size = item.modify({}, data, contenttype_guessed=contenttype)
        item_modified.send(app._get_current_object(),
                           fqname=item.fqname, action=ACTION_SAVE)
        jfu_server_lock.release()
        return jsonify(name=subitem_name,
                       size=size,
                       url=url_for('.show_item', item_name=item_name, rev=revid),
                       contenttype=contenttype_to_class(contenttype),
        )
    except AccessDenied:
        jfu_server_lock.release()
        abort(403)


def contenttype_selects_gen():
    for g in content_registry.group_names:
        description = u', '.join([e.display_name for e in content_registry.groups[g]])
        yield g, None, description
    yield u'Unknown Items', None, u'Items of contenttype unknown to MoinMoin'

ContenttypeGroup = MultiSelect.of(Enum.out_of(contenttype_selects_gen())).using(optional=True)


class IndexForm(Form):
    contenttype = ContenttypeGroup
    submit_label = L_('Filter')


@frontend.route('/+index/', defaults=dict(item_name=''), methods=['GET', 'POST'])
@frontend.route('/+index/<itemname:item_name>', methods=['GET', 'POST'])
def index(item_name):

    def name_initial(files, uppercase=False, lowercase=False):
        """
        return a sorted list of first characters of subitem names,
        optionally all uppercased or lowercased.
        """
        initials = set()
        for item in files:
            if isinstance(item.meta.revision.data, file):
                item.meta.revision.data.close()
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
    selected_groups = form['contenttype'].value
    startswith = request.values.get("startswith")
    dirs, files = item.get_index(startswith, selected_groups)
    dirs_fullname = [x.fullname for x in dirs]
    initials = name_initial(files, uppercase=True)
    fqname = item.fqname
    if fqname.value == NAMESPACE_ALL:
        fqname = CompositeName(NAMESPACE_ALL, NAME_EXACT, u'')
    item_names = item_name.split(u'/')
    ns_len = len(item.meta['namespace']) + 1 if item.meta['namespace'] else 0

    # detect orphan subitems and make a list of their missing parents
    used_dirs = set()
    for file_ in files:
        # if file_ in dirs:  # XXX if true the file is opened twice, windows servers will not be able to destroy file until after python garbage collection
        if file_.fullname in dirs_fullname:
            used_dirs.add(file_[0])
    all_dirs = set(x[0] for x in dirs)
    missing_dirs = all_dirs - used_dirs

    if item_name:
        what = ''
        if item.fqname.value == NAMESPACE_ALL:
            title = _("Global Index of All Namespaces")
        elif item.meta['namespace']:
            what = _("Namespace '%(name)s' ", name=item.meta['namespace'])
            subitem = item_name[ns_len:]
            if subitem:
                what = what + _("subitems '%(item_name)s'", item_name=subitem)
            title = _("Index of %(what)s", what=what)
        else:
            title = _("Index of subitems '%(item_name)s'", item_name=item_name)
    else:
        title = _("Global Index")

    return render_template('index.html',
                           title_name='Global Index',
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
    )


@frontend.route('/+mychanges')
def mychanges():
    """
    Returns the list of all items the current user has contributed to.

    :returns: a page with all the items the current user has contributed to
    """
    offset = request.values.get('offset', 0)
    offset = max(int(offset), 0)
    if flaskg.user.valid:
        results_per_page = flaskg.user.results_per_page
    else:
        results_per_page = app.cfg.results_per_page
    my_changes = _mychanges(flaskg.user.itemid)
    my_changes_page = util.getPageContent(my_changes, offset, results_per_page)

    return render_template('mychanges.html',
                           title_name=_(u'My Changes'),
                           headline=_(u'My Changes'),
                           my_changes_page=my_changes_page,
    )


def _mychanges(userid):
    """
    Returns a list with all fqnames of items which user userid has contributed to.

    :param userid: user itemid
    :type userid: unicode
    :returns: the list of all items with user userid's contributions
    """
    q = And([Term(WIKINAME, app.cfg.interwikiname),
             Term(USERID, userid)])
    revs = flaskg.storage.search(q, idx_name=ALL_REVS, sortedby=[MTIME], reverse=True, limit=None)
    # get rid of the content value to save potentially big amounts of memory:
    history = []
    for rev in revs:
        entry = dict(rev.meta)
        entry[FQNAME] = rev.fqname
        entry[FQNAMES] = rev.fqnames
        history.append(entry)
    return history


def shorten_item_id(name, length=7):
    """
    Shorten IDs starting with @itemid/ to specified length,
    """
    if name.startswith('@itemid/'):
        return name[8:8 + length]
    return name


@frontend.route('/+forwardrefs/<itemname:item_name>')
def forwardrefs(item_name):
    """
    Returns the list of all links or transclusions of item item_name

    :param item_name: the name of the current item
    :type item_name: unicode
    :returns: a page with all the items linked from this item
    """
    refs = _forwardrefs(item_name)
    return render_template('link_list_item_panel.html',
                           item_name=item_name,
                           fqname=split_fqname(item_name),
                           headline=_(u"Items that are referred by '%(item_name)s'", item_name=shorten_item_id(item_name)),
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


@frontend.route('/+backrefs/<itemname:item_name>')
def backrefs(item_name):
    """
    Returns the list of all items that link or transclude item_name

    :param item_name: the name of the current item
    :type item_name: unicode
    :returns: a page with all the items which link or transclude item_name
    """
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    refs_here = _backrefs(item_name)
    return render_template('link_list_item_panel.html',
                           item=item,
                           item_name=item_name,
                           fqname=split_fqname(item_name),
                           headline=_(u"Items which refer to '%(item_name)s'", item_name=shorten_item_id(item_name)),
                           fq_names=refs_here,
    )


def _backrefs(item_name):
    """
    Returns a list with all names of items which ref fq_name

    :param item_name: the name of the item transcluded or linked
    :type item_name: unicode
    :returns: the list of all items which ref fq_name
    """
    q = And([Term(WIKINAME, app.cfg.interwikiname),
             Or([Term(ITEMTRANSCLUSIONS, item_name), Term(ITEMLINKS, item_name)])])
    revs = flaskg.storage.search(q)
    return set([fqname for rev in revs for fqname in rev.fqnames])


@frontend.route('/+history/<itemname:item_name>')
def history(item_name):
    fqname = split_fqname(item_name)
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)

    offset = request.values.get('offset', 0)
    offset = max(int(offset), 0)
    bookmark_time = int(request.values.get('bookmark', 0))
    if flaskg.user.valid:
        results_per_page = flaskg.user.results_per_page
    else:
        results_per_page = app.cfg.results_per_page
    terms = [Term(WIKINAME, app.cfg.interwikiname), ]
    terms.extend(Term(term, value) for term, value in fqname.query.iteritems())
    if bookmark_time:
        terms.append(DateRange(MTIME, start=datetime.utcfromtimestamp(bookmark_time), end=None))
    query = And(terms)
    # TODO: due to how getPageContent and the template works, we need to use limit=None -
    # it would be better to use search_page (and an appropriate limit, if needed)
    revs = flaskg.storage.search(query, idx_name=ALL_REVS, sortedby=[MTIME], reverse=True, limit=None)
    # get rid of the content value to save potentially big amounts of memory:
    history = []
    for rev in revs:
        entry = dict(rev.meta)
        entry[FQNAME] = rev.fqname
        entry[FQNAMES] = rev.fqnames
        history.append(entry)
        if isinstance(rev.data, file):
            rev.data.close()
    history_page = util.getPageContent(history, offset, results_per_page)
    if isinstance(item.rev.data, file):
        item.rev.data.close()
    ret = render_template('history.html',
                          fqname=fqname,
                          item=item,
                          item_name=item_name,
                          history_page=history_page,
                          bookmark_time=bookmark_time,
                          NAME_EXACT=NAME_EXACT,
                          len=len,
    )
    if isinstance(item.rev.data, file):
        item.rev.data.close()
    return ret


@frontend.route('/<namespace>/+history')
@frontend.route('/+history', defaults=dict(namespace=NAMESPACE_DEFAULT), methods=['GET'])
def global_history(namespace):
    all_revs = bool(request.values.get('all'))
    idx_name = ALL_REVS if all_revs else LATEST_REVS
    terms = [Term(WIKINAME, app.cfg.interwikiname)]
    fqname = CompositeName(NAMESPACE_ALL, NAME_EXACT, u'')
    if namespace != NAMESPACE_ALL:
        terms.append(Term(NAMESPACE, namespace))
        fqname = split_fqname(namespace)
    bookmark_time = flaskg.user.bookmark
    if bookmark_time is not None:
        terms.append(DateRange(MTIME, start=datetime.utcfromtimestamp(bookmark_time), end=None))
    query = And(terms)
    revs = flaskg.storage.search(query, idx_name=idx_name, sortedby=[MTIME], reverse=True, limit=1000)
    # Group by date
    history = []
    day_history = namedtuple('day_history', ['day', 'entries'])
    prev_date = '0000-00-00'
    dh = day_history(prev_date, [])  # dummy
    for rev in revs:
        rev_date = format_date(datetime.utcfromtimestamp(rev.meta[MTIME]))
        if rev_date == prev_date:
            dh.entries.append(rev)
        else:
            history.append(dh)
            dh = day_history(rev_date, [rev])
            prev_date = rev_date
    else:
        history.append(dh)
    del history[0]  # kill the dummy

    title_name = _(u'Global History')
    if namespace == NAMESPACE_ALL:
        title = _("Global History of All Namespaces")
    elif namespace:
        title = _("History of Namespace '%(namespace)s'", namespace=namespace)
    else:
        title = _("Global History")
    current_timestamp = int(time.time())
    return render_template('global_history.html',
                           title_name=title_name,
                           history=history,
                           current_timestamp=current_timestamp,
                           bookmark_time=bookmark_time,
                           fqname=fqname,
                           title=title,
    )


def _compute_item_sets():
    """
    compute sets of existing, linked, transcluded and no-revision item fqnames
    """
    linked = set()
    transcluded = set()
    existing = set()
    revs = flaskg.storage.documents(wikiname=app.cfg.interwikiname)
    for rev in revs:
        existing |= set(rev.fqnames)
        linked.update(rev.meta.get(ITEMLINKS, []))
        transcluded.update(rev.meta.get(ITEMTRANSCLUSIONS, []))
    return existing, set(split_fqname_list(linked)), set(split_fqname_list(transcluded))


def split_fqname_list(names):
    """
    Converts a list of names to a list of fqnames.
    """
    return [split_fqname(name) for name in names]


@frontend.route('/+wanteds')
def wanted_items():
    """
    Returns a list view of non-existing items that are linked to or
    transcluded by other items. If you want to know by which items they are
    referred to, use the backrefs functionality of the item in question.
    """
    existing, linked, transcluded = _compute_item_sets()
    referred = linked | transcluded
    wanteds = referred - existing
    title_name = _(u'Wanted Items')
    return render_template('link_list_no_item_panel.html',
                           headline=_(u'Wanted Items'),
                           title_name=title_name,
                           fq_names=wanteds)


@frontend.route('/+orphans')
def orphaned_items():
    """
    Return a list view of existing items not being linked or transcluded
    by any other item (which makes them sometimes not discoverable).
    """
    existing, linked, transcluded = _compute_item_sets()
    referred = linked | transcluded
    orphans = existing - referred
    title_name = _('Orphaned Items')
    return render_template('link_list_no_item_panel.html',
                           title_name=title_name,
                           headline=_(u'Orphaned Items'),
                           fq_names=orphans)


@frontend.route('/+quicklink/<itemname:item_name>')
def quicklink_item(item_name):
    """ Add/Remove the current wiki page to/from the user quicklinks """
    u = flaskg.user
    msg = None
    if not u.valid:
        msg = _("You must login to use this action: %(action)s.", action="quicklink/quickunlink"), "error"
    elif not flaskg.user.is_quicklinked_to([item_name]):
        if not u.quicklink(item_name):
            msg = _('A quicklink to this page could not be added for you.'), "error"
    else:
        if not u.quickunlink(item_name):
            msg = _('Your quicklink to this page could not be removed.'), "error"
    if msg:
        flash(*msg)
    return redirect(url_for_item(item_name))


@frontend.route('/+subscribe/<itemname:item_name>')
def subscribe_item(item_name):
    """ Add/Remove the current wiki item to/from the user's subscriptions """
    u = flaskg.user
    cfg = app.cfg
    msg = None
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)
    if not u.valid:
        msg = _("You must login to use this action: %(action)s.", action="subscribe/unsubscribe"), "error"
    elif not u.may.read(item_name):
        msg = _("You are not allowed to subscribe to an item you may not read."), "error"
    elif u.is_subscribed_to(item):
        # Try to unsubscribe
        if not u.unsubscribe(ITEMID, item.meta[ITEMID]):
            msg = _(
                "Can't remove the subscription! You are subscribed to this page in some other way.") + u' ' + _(
                "Please edit the subscription in your settings."), "error"
    else:
        # Try to subscribe
        if not u.subscribe(ITEMID, item.meta[ITEMID]):
            msg = _('You could not get subscribed to this item.'), "error"
    if msg:
        flash(*msg)
    return redirect(url_for_item(item_name))


class ValidRegistration(Validator):
    """Validator for a valid registration form
    """
    passwords_mismatch_msg = L_('The passwords do not match.')

    def validate(self, element, state):
        if not (element['username'].valid and
                element['password1'].valid and element['password2'].valid and
                element['email'].valid and element['textcha'].valid):
            return False
        if element['password1'].value != element['password2'].value:
            return self.note_error(element, state, 'passwords_mismatch_msg')
        return True


class RegistrationForm(TextChaizedForm):
    """a simple user registration form"""
    name = 'register'

    username = RequiredText.using(label=L_('Username')).with_properties(placeholder=L_("The login username you want to use"), autofocus=True)
    password1 = RequiredPassword.with_properties(placeholder=L_("The login password you want to use"))
    password2 = RequiredPassword.with_properties(placeholder=L_("Repeat the same password"))
    email = YourEmail
    openid = YourOpenID.using(optional=True)
    submit_label = L_('Register')

    validators = [ValidRegistration()]


class OpenIDForm(RegistrationForm):
    """
    OpenID registration form, inherited from the simple registration form.
    """
    name = 'openid'

    openid = YourOpenID


def _using_moin_auth():
    """Check if MoinAuth is being used for authentication.

    Only then users can register with moin or change their password via moin.
    """
    from MoinMoin.auth import MoinAuth
    for auth in app.cfg.auth:
        if isinstance(auth, MoinAuth):
            return True
    return False


def _using_openid_auth():
    """Check if OpenIDAuth is being used for authentication.

    Only then users can register with openid or change their password via openid.
    """
    from MoinMoin.auth.openidrp import OpenIDAuth
    for auth in app.cfg.auth:
        if isinstance(auth, OpenIDAuth):
            return True
    return False


@frontend.route('/+register', methods=['GET', 'POST'])
def register():
    title_name = _(u'Register')
    isOpenID = 'openid_submit' in request.values

    if isOpenID:
        # this is an openid continuation
        if not _using_openid_auth():
            return Response('No OpenIDAuth in auth list', 403)
        template = 'openid_register.html'
        FormClass = OpenIDForm
    else:
        # not openid registration and no MoinAuth
        if not _using_moin_auth():
            return Response('No MoinAuth in auth list', 403)
        template = 'register.html'
        FormClass = RegistrationForm

    if request.method in ['GET', 'HEAD']:
        form = FormClass.from_defaults()
        if isOpenID:
            oid = request.values.get('openid_openid')
            if oid:
                form['openid'] = oid
        TextCha(form).amend_form()
    elif request.method == 'POST':
        form = FormClass.from_flat(request.form)
        TextCha(form).amend_form()

        if form.validate():
            user_kwargs = {
                'username': form['username'].value,
                'password': form['password1'].value,
                'email': form['email'].value,
                'openid': form['openid'].value,
            }
            if app.cfg.user_email_verification:
                user_kwargs['is_disabled'] = True
                user_kwargs['verify_email'] = True
            msg = user.create_user(**user_kwargs)
            if msg:
                flash(msg, "error")
            else:
                if app.cfg.user_email_verification:
                    u = user.User(auth_username=user_kwargs['username'])
                    is_ok, msg = u.mail_email_verification()
                    if is_ok:
                        flash(_('Account verification required, please see the email we sent to your address.'), "info")
                    else:
                        flash(_('An error occurred while sending the verification email: "%(message)s" '
                                'Please contact an administrator to activate your account.',
                                message=msg), "error")
                else:
                    flash(_('Account created, please log in now.'), "info")
                return redirect(url_for('.show_root'))

    return render_template(template,
                           title_name=title_name,
                           form=form,
    )


@frontend.route('/+verifyemail', methods=['GET'])
def verifyemail():
    u = token = None
    if 'username' in request.values and 'token' in request.values:
        u = user.User(auth_username=request.values['username'])
        token = request.values['token']
    success = False
    if u and token and u.validate_recovery_token(token):
        unvalidated_email = u.profile[EMAIL_UNVALIDATED]
        if app.cfg.user_email_unique and user.search_users(**{EMAIL: unvalidated_email}):
            msg = _('This email is already in use.')
        else:
            if u.disabled:
                u.profile[DISABLED] = False
                msg = _('Your account has been activated, you can log in now.')
            else:
                msg = _('Your new email address has been confirmed.')
            u.profile[EMAIL] = unvalidated_email
            del u.profile[EMAIL_UNVALIDATED]
            del u.profile[RECOVERPASS_KEY]
            success = True
    else:
        msg = _('Your username and/or token is invalid!')
    if success:
        u.save()
        flash(msg, 'info')
    else:
        flash(msg, 'error')
    return redirect(url_for('.show_root'))


class ValidLostPassword(Validator):
    """Validator for a valid lost password form
    """
    name_or_email_needed_msg = L_('Your user name or your email address is needed.')

    def validate(self, element, state):
        if not(element['username'].valid and element['username'].value or
               element['email'].valid and element['email'].value):
            return self.note_error(element, state, 'name_or_email_needed_msg')

        return True


class PasswordLostForm(Form):
    """a simple password lost form"""
    name = 'lostpass'

    username = OptionalText.using(label=L_('Name')).with_properties(placeholder=L_("Your login name"))
    email = YourEmail.using(optional=True)
    submit_label = L_('Recover password')

    validators = [ValidLostPassword()]


@frontend.route('/+lostpass', methods=['GET', 'POST'])
def lostpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    title_name = _(u'Lost Password')

    if not _using_moin_auth():
        return Response('No MoinAuth in auth list', 403)

    if request.method in ['GET', 'HEAD']:
        form = PasswordLostForm.from_defaults()
    elif request.method == 'POST':
        form = PasswordLostForm.from_flat(request.form)
        if form.validate():
            u = None
            username = form['username'].value
            if username:
                u = user.User(auth_username=username)
            email = form['email'].value
            if form['email'].valid and email:
                users = user.search_users(email=email)
                u = users and user.User(users[0].meta[ITEMID])
            if u and u.valid:
                is_ok, msg = u.mail_password_recovery()
                if not is_ok:
                    flash(msg, "error")
            flash(_("If this account exists, you will be notified."), "info")
            return redirect(url_for('.show_root'))
    return render_template('lostpass.html',
                           title_name=title_name,
                           form=form,
    )


class ValidPasswordRecovery(Validator):
    """Validator for a valid password recovery form
    """
    passwords_mismatch_msg = L_('The passwords do not match.')
    password_problem_msg = L_('New password is unacceptable, could not get processed.')

    def validate(self, element, state):
        if element['password1'].value != element['password2'].value:
            return self.note_error(element, state, 'passwords_mismatch_msg')

        password = element['password1'].value
        try:
            app.cfg.cache.pwd_context.encrypt(password)
        except (ValueError, TypeError) as err:
            return self.note_error(element, state, 'password_problem_msg')

        return True


class PasswordRecoveryForm(Form):
    """a simple password recovery form"""
    name = 'recoverpass'

    username = RequiredText.using(label=L_('Name')).with_properties(placeholder=L_("Your login name"))
    token = RequiredText.using(label=L_('Recovery token')).with_properties(
        placeholder=L_("The recovery token that has been sent to you"))
    password1 = RequiredPassword.using(label=L_('New password')).with_properties(
        placeholder=L_("The login password you want to use"))
    password2 = RequiredPassword.using(label=L_('New password (repeat)')).with_properties(
        placeholder=L_("Repeat the same password"))
    submit_label = L_('Change password')

    validators = [ValidPasswordRecovery()]


@frontend.route('/+recoverpass', methods=['GET', 'POST'])
def recoverpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    title_name = _(u'Recover Password')

    if not _using_moin_auth():
        return Response('No MoinAuth in auth list', 403)

    if request.method in ['GET', 'HEAD']:
        form = PasswordRecoveryForm.from_defaults()
        form.update(request.values)
    elif request.method == 'POST':
        form = PasswordRecoveryForm.from_flat(request.form)
        if form.validate():
            u = user.User(auth_username=form['username'].value)
            if u and u.valid and u.apply_recovery_token(form['token'].value, form['password1'].value):
                flash(_("Your password has been changed, you can log in now."), "info")
            else:
                flash(_('Your token is invalid!'), "error")
            return redirect(url_for('.show_root'))
    return render_template('recoverpass.html',
                           title_name=title_name,
                           form=form,
    )


class ValidLogin(Validator):
    """
    Login validator
    """
    moin_fail_msg = L_('Either your username or password was invalid.')
    openid_fail_msg = L_('Failed to authenticate with this OpenID.')

    def validate(self, element, state):
        # get the result from the other validators
        moin_valid = element['username'].valid and element['password'].valid
        openid_valid = element['openid'].valid

        # none of them was valid
        if not (openid_valid or moin_valid):
            return False
        # got our user!
        if flaskg.user.valid:
            return True
        # no valid user -> show appropriate message
        else:
            if not openid_valid:
                return self.note_error(element, state, 'openid_fail_msg')
            elif not moin_valid:
                return self.note_error(element, state, 'moin_fail_msg')


class LoginForm(Form):
    """
    Login form
    """
    name = 'login'

    username = RequiredText.using(label=L_('Username'), optional=False).with_properties(autofocus=True)
    password = RequiredPassword
    openid = YourOpenID.using(optional=True)
    nexturl = Hidden.using(default='')
    # This field results in a login_submit field in the POST form, which is in
    # turn looked for by setup_user() in app.py as marker for login requests.
    submit = Hidden.using(default='1')
    submit_label = L_('Log in')

    validators = [ValidLogin()]


@frontend.route('/+login', methods=['GET', 'POST'])
def login():
    if flaskg.user.valid:
        flash(_("You are logged in."), "info")
        form = LoginForm.from_flat(request.form)
        nexturl = form['nexturl']
        return redirect(nexturl)
    title_name = _(u'Login')

    # multistage return
    if flaskg._login_multistage_name == 'openid':
        return Response(flaskg._login_multistage, mimetype='text/html')

    if request.method in ['GET', 'HEAD']:
        form = LoginForm.from_defaults()
        next_url = request.referrer or url_for('.show_root')
        if not next_url.startswith(request.host_url) or '/+' in next_url:
            next_url = url_for('.show_root')
        form['nexturl'].set(next_url)
        for authmethod in app.cfg.auth:
            hint = authmethod.login_hint()
            if hint:
                flash(hint, "info")
    elif request.method == 'POST':
        # this is executed when login fails do to bad ID or pw - app.py > def setup_user does successful logins
        form = LoginForm.from_flat(request.form)
        if form.validate():
            # is this dead code? we have a logged-in, valid user
            nexturl = form['nexturl']
            return redirect(nexturl)
        # flash the error messages (if any)
        for msg in flaskg._login_messages:
            flash(msg, "error")
    return render_template('login.html',
                           title_name=title_name,
                           login_inputs=app.cfg.auth_login_inputs,
                           form=form,
    )


@frontend.route('/+logout')
def logout():
    flash(_("You are logged out."), "info")
    flaskg.user.logout_session()
    next_url = request.referrer or url_for('.show_root')
    if not next_url.startswith(request.host_url) or '/+' in next_url:
        next_url = url_for('.show_root')
    return redirect(next_url)


class ValidChangePass(Validator):
    """Validator for a valid password change
    """
    passwords_mismatch_msg = L_('The passwords do not match.')
    current_password_wrong_msg = L_('The current password was wrong.')
    password_problem_msg = L_('New password is unacceptable, could not get processed.')

    def validate(self, element, state):
        password_not_accepted_msg = L_('New password not acceptable: ')

        if not (element['password_current'].valid and element['password1'].valid and element['password2'].valid):
            return False

        if not user.User(name=flaskg.user.name, password=element['password_current'].value).valid:
            return self.note_error(element, state, 'current_password_wrong_msg')

        if element['password1'].value != element['password2'].value:
            return self.note_error(element, state, 'passwords_mismatch_msg')

        password = element['password1'].value
        pw_checker = app.cfg.password_checker
        if pw_checker:
            pw_error = pw_checker(flaskg.user.name[0], password)
            if pw_error:
                return self.note_error(element, state, message=password_not_accepted_msg + pw_error)
        try:
            app.cfg.cache.pwd_context.encrypt(password)
        except (ValueError, TypeError) as err:
            return self.note_error(element, state, 'password_problem_msg')
        return True


class UserSettingsPasswordForm(Form):
    name = 'usersettings_password'
    validators = [ValidChangePass()]

    password_current = RequiredPassword.using(label=L_('Current Password')).with_properties(
        placeholder=L_("Your current login password"))
    password1 = RequiredPassword.using(label=L_('New password')).with_properties(
        placeholder=L_("The login password you want to use"))
    password2 = RequiredPassword.using(label=L_('New password (repeat)')).with_properties(
        placeholder=L_("Repeat the same password"))
    submit_label = L_('Change password')


class UserSettingsNotificationForm(Form):
    name = 'usersettings_notification'
    email = YourEmail
    submit_label = L_('Save')


class UserSettingsQuicklinksForm(Form):
    """
    No validation is performed as lots of things are valid, existing items, non-existing items, external links, mailto, external wiki links...
    """
    name = 'usersettings_quicklinks'
    quicklinks = Quicklinks
    submit_label = L_('Save')


class UserSettingsOptionsForm(Form):
    name = 'usersettings_options'
    mailto_author = Checkbox.using(label=L_('Publish my email (not my wiki homepage) in author info'))
    edit_on_doubleclick = Checkbox.using(label=L_('Open editor on double click'))
    scroll_page_after_edit = Checkbox.using(label=L_('Scroll page after edit'))
    show_comments = Checkbox.using(label=L_('Show comment sections'))
    disabled = Checkbox.using(label=L_('Disable this account forever'))
    submit_label = L_('Save')


class ValidSubscriptions(Validator):
    """Validator for a subscriptions change
    """

    def validate(self, element, state):
        # TODO: is additional validation for namespaces, itemids, names, or name prefixes needed?
        invalid_subscription_msg = L_('Invalid subscription syntax: ')
        invalid_keyword = L_('Invalid keyword: ')
        invalid_re_expression = L_('Invalid RE syntax: ')
        errors = []
        for subscription in element.value['subscriptions']:
            try:
                keyword, value = subscription.split(":", 1)
            except ValueError:
                errors.append(invalid_subscription_msg + subscription)
                continue
            if keyword == ITEMID:
                continue
            if keyword not in (NAME, NAMEPREFIX, TAGS, NAMERE, ):
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
            return self.note_error(element, state, message=', '.join(errors))
        return True


class UserSettingsSubscriptionsForm(Form):
    name = 'usersettings_subscriptions'
    subscriptions = Subscriptions
    submit_label = L_('Save')

    validators = [ValidSubscriptions()]


@frontend.route('/+usersettings', methods=['GET', 'POST'])
def usersettings():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    title_name = _('User Settings')

    # these forms can't be global because we need app object, which is only available within a request:
    class UserSettingsPersonalForm(Form):
        name = 'usersettings_personal'  # "name" is duplicate
        name = Names.using(label=L_('Usernames')).with_properties(placeholder=L_("The login usernames you want to use"))
        display_name = OptionalText.using(label=L_('Display-Name')).with_properties(
            placeholder=L_("Your display name (informational)"))
        openid = YourOpenID.using(optional=True)
        # _timezones_keys = sorted(Locale('en').time_zones.keys())
        _timezones_keys = [unicode(tz) for tz in pytz.common_timezones]
        timezone = Select.using(label=L_('Timezone')).out_of((e, e) for e in _timezones_keys)
        _supported_locales = [Locale('en')] + app.babel_instance.list_translations()
        locale = Select.using(label=L_('Locale')).out_of(
            ((unicode(l), l.display_name) for l in _supported_locales), sort_by=1)
        submit_label = L_('Save')

    class UserSettingsUIForm(Form):
        name = 'usersettings_ui'
        theme_name = Select.using(label=L_('Theme name')).out_of(
            ((unicode(t.identifier), t.name) for t in get_themes_list()), sort_by=1)
        css_url = URL.using(label=L_('User CSS URL'), optional=True).with_properties(
            placeholder=L_("Give the URL of your custom CSS (optional)"))
        edit_rows = Natural.using(label=L_('Number rows in edit textarea')).with_properties(
            placeholder=L_("Editor textarea height (0=auto)"))
        results_per_page = Natural.using(label=L_('History results per page')).with_properties(
            placeholder=L_("Number of results per page (0=no paging)"))
        submit_label = L_('Save')

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
        return redirect(url_for('.login'))

    if request.method == 'POST':
        part = request.form.get('part')
        if part not in form_classes:
            # the current part does not exist
            if request.is_xhr:
                # if the request is made via XHR, we return 404 Not Found
                abort(404)
            # otherwise we basically fall back to a normal GET request
            part = None

        if part:
            # create form object from request.form
            form = form_classes[part].from_flat(request.form)

            # save response to a dict as we can't use HTTP redirects or flash() for XHR requests
            response = dict(
                form=None,
                flash=[],
                redirect=None,
            )

            if form.validate():
                # successfully modified everything
                success = True
                if part == 'password':
                    flaskg.user.set_password(form['password1'].value)
                    flaskg.user.save()
                    response['flash'].append((_("Your password has been changed."), "info"))
                else:
                    if part == 'personal':
                        if (form['openid'].value and form['openid'].value != flaskg.user.openid and
                                user.search_users(openid=form['openid'].value)):
                            # duplicate openid
                            response['flash'].append((_("This openid is already in use."), "error"))
                            success = False
                        if set(form['name'].value) != set(flaskg.user.name):
                            new_names = set(form['name'].value) - set(flaskg.user.name)
                            for name in new_names:
                                if user.search_users(**{NAME_EXACT: name}):
                                    # duplicate name
                                    response['flash'].append((_("The username '%(name)s' is already in use.", name=name),
                                                              "error"))
                                    success = False
                    if part == 'notification':
                        if (form['email'].value != flaskg.user.email and
                                user.search_users(**{EMAIL: form['email'].value}) and app.cfg.user_email_unique):
                            # duplicate email
                            response['flash'].append((_('This email is already in use'), 'error'))
                            success = False
                    if success:
                        user_old_email = flaskg.user.email
                        d = dict(form.value)
                        for k, v in d.items():
                            flaskg.user.profile[k] = v
                        if (part == 'notification' and app.cfg.user_email_verification and
                                form['email'].value != user_old_email):
                            flaskg.user.profile[EMAIL] = user_old_email
                            flaskg.user.profile[EMAIL_UNVALIDATED] = form['email'].value
                            # send verification mail
                            is_ok, msg = flaskg.user.mail_email_verification()
                            if is_ok:
                                response['flash'].append(
                                    (_('A confirmation email has been sent to your '
                                       'newly configured email address.'), "info"))
                                response['redirect'] = url_for('.show_root')
                            else:
                                # sending the verification email didn't work.
                                # delete the unvalidated email and alert the user.
                                del flaskg.user.profile[EMAIL_UNVALIDATED]
                                response['flash'].append((_('Your email address was not changed because sending the '
                                                            'verification email failed. Please try again later.'),
                                                          "error"))
                        else:
                            flaskg.user.save()
            else:
                # validation failed
                response['flash'].append((_("Nothing saved."), "error"))
            if not response['flash']:
                # if no flash message was added until here, we add a generic success message
                response['flash'].append((_("Your changes have been saved."), "info"))

            if response['redirect'] is not None or not request.is_xhr:
                # if we redirect or it is no XHR request, we just flash() the messages normally
                for f in response['flash']:
                    flash(*f)

            if request.is_xhr:
                # if it is a XHR request, render the part from the usersettings_ajax.html template
                # and send the response encoded as an JSON object
                response['form'] = render_template('usersettings_ajax.html',
                                                   part=part,
                                                   form=form,
                )
                return jsonify(**response)
            else:
                # if it is not a XHR request but there is an redirect pending, we use a normal HTTP redirect
                if response['redirect'] is not None:
                    return redirect(response['redirect'])

            # if the view did not return until here, we add the current form to the forms dict
            # and continue with rendering the normal template
            forms[part] = form

    # initialize all remaining forms
    for p, FormClass in form_classes.iteritems():
        if p not in forms:
            forms[p] = FormClass.from_object(flaskg.user)

    return render_template('usersettings.html',
                           title_name=title_name,
                           form_objs=forms,
    )


@frontend.route('/+bookmark')
def bookmark():
    """ set bookmark (in time) for recent changes (or delete them) """
    if flaskg.user.valid:
        timestamp = request.values.get('time')
        if timestamp is not None:
            if timestamp == 'del':
                tm = None
            else:
                try:
                    tm = int(timestamp)
                except StandardError:
                    tm = int(time.time())
        else:
            tm = int(time.time())
        flaskg.user.bookmark = tm
    else:
        flash(_("You must log in to use bookmarks."), "error")
    return redirect(url_for('.global_history'))


def get_revs():
    """
    get 2 revids from values
    """
    rev1 = request.values.get('rev1')
    rev2 = request.values.get('rev2')
    if rev1 is None:
        # we require at least rev1
        abort(404)
    if rev2 is None:
        # rev2 is optional, use current rev if not given
        rev2 = CURRENT
    return rev1, rev2


@frontend.route('/+diffraw/<itemname:item_name>')
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


@frontend.route('/+diff/<itemname:item_name>')
def diff(item_name):
    """
    Find 2 revisions suitable for a diff and return a formatted diff view.

    Workaround the issues noted in #579 where the url generated by Global History
    may point to non-existent revisions.
    """
    item = flaskg.storage[item_name]
    revs = sorted([(rev.meta[MTIME], rev.revid) for rev in item.iter_revs()], reverse=True)
    if not revs:
        abort(404)
    bookmark_time = request.values.get('bookmark')
    if bookmark_time is not None:
        # when called from Global History or "recent changes" there may be a bookmark time
        # try to find the latest rev1 before bookmark <date>
        for mtime, revid in revs:
            if mtime <= int(bookmark_time):
                rev1 = revid
                break
        else:
            rev1 = revs[-1][1]  # if we didn't find a rev, we just take oldest rev we have
        rev2 = revs[0][1]  # and compare it with latest we have
    else:
        # otherwise we try get the 2 revids directly
        rev1 = request.values.get('rev1')
        rev2 = request.values.get('rev2')
        rev_ids = [x[1] for x in revs]
        if rev1 not in rev_ids:
            rev1 = revs[-1][1]  # take oldest rev we have - there may only one rev
        if rev2 not in rev_ids:
            rev2 = revs[0][1]  # the latest rev we have
    return _diff(item, rev1, rev2)


def _common_type(ct1, ct2):
    if ct1 == ct2:
        # easy, exactly the same content type, call do_diff for it
        commonmt = ct1
    else:
        major1 = ct1.split('/')[0]
        major2 = ct2.split('/')[0]
        if major1 == major2:
            # at least same major mimetype, use common base item class
            commonmt = major1 + '/'
        else:
            # nothing in common
            commonmt = ''
    return commonmt


def _crash(item, oldrev, newrev):
    error_id = uuid.uuid4()
    logging.exception("An exception happened in _render_data (error_id = %s ):" % error_id)
    return render_template("crash_view.html",
                           server_time=time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                           url=request.url,
                           error_id=error_id,
                           oldrev=oldrev,
                           newrev=newrev,
                           fqname=item.fqname,
                           item=item,
    )


def _diff(item, revid1, revid2):
    try:
        oldrev = item[revid1]
        newrev = item[revid2]
    except KeyError:
        abort(404)
    if oldrev.meta['mtime'] > newrev.meta['mtime']:
        # within diff, always place oldest on left, newest on right
        oldrev, newrev = newrev, oldrev
        revid1, revid2 = revid2, revid1
    commonmt = _common_type(oldrev.meta[CONTENTTYPE], newrev.meta[CONTENTTYPE])
    try:
        item = Item.create(item.name, contenttype=commonmt, rev_id=newrev.revid)
    except AccessDenied:
        abort(403)

    # create dict containing older and newer revids to be used in formatting links
    terms = [Term(WIKINAME, app.cfg.interwikiname), ]
    terms.extend(Term(term, value) for term, value in item.fqname.query.iteritems())
    query = And(terms)
    rev_ids = flaskg.storage.search(query, idx_name=ALL_REVS, sortedby=[MTIME], reverse=False, limit=None)
    rev_ids = [x.meta for x in rev_ids]
    # we do not do diffs across item IDs should an item be deleted and recreated with same name
    item_id = rev_ids[-1]['itemid']
    rev_ids = [x['revid'] for x in rev_ids if x['itemid'] == item_id]
    rev_links = {}
    if len(rev_ids) > 2:
        rev1_idx = rev_ids.index(revid1)
        rev2_idx = rev_ids.index(revid2)
        if rev1_idx > 0:
            rev_links['r1_oldest'] = rev_ids[0]
            rev_links['r1_older'] = rev_ids[rev1_idx - 1]
        if rev2_idx > rev1_idx + 1:
            rev_links['r1_newer'] = rev_ids[rev1_idx + 1]
        end = len(rev_ids) - 1
        if rev2_idx < end:
            rev_links['r2_newer'] = rev_ids[rev2_idx + 1]
            rev_links['r2_newest'] = rev_ids[-1]
        if rev2_idx > rev1_idx + 1:
            rev_links['r2_older'] = rev_ids[rev2_idx - 1]
    if rev_links:
        rev_links['revid1'] = revid1
        rev_links['revid2'] = revid2

    try:
        diff_html = Markup(item.content._render_data_diff(oldrev, newrev, rev_links=rev_links))
    except Exception:
        return _crash(item, oldrev, newrev)

    return render_template('diff.html',
                           item=item, item_name=item.name,
                           fqname=item.fqname,
                           diff_html=diff_html,
                           rev=item.rev,
                           rev_links=rev_links,
                           oldrev=oldrev,
                           newrev=newrev,
    )


def _diff_raw(item, revid1, revid2):
    oldrev = item[revid1]
    newrev = item[revid2]
    if oldrev.meta['mtime'] > newrev.meta['mtime']:
        oldrev, newrev = newrev, oldrev
        revid1, revid2 = revid2, revid1
    commonmt = _common_type(oldrev.meta[CONTENTTYPE], newrev.meta[CONTENTTYPE])

    try:
        item = Item.create(item.name, contenttype=commonmt, rev_id=newrev.revid)
    except AccessDenied:
        abort(403)
    return item.content._render_data_diff_raw(oldrev, newrev)


@frontend.route('/+similar_names/<itemname:item_name>')
def similar_names(item_name):
    """
    list similar item names
    """
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    fq_name = split_fqname(item_name)
    start, end, matches = findMatches(fq_name)
    keys = sorted(matches.keys())
    # TODO later we could add titles for the misc ranks:
    # 8 item_name
    # 4 "{0}/...".format(item_name)
    # 3 "{0}...{1}".format(start, end)
    # 1 "{0}...".format(start)
    # 2 "...{1}".format(end)
    fq_names = []
    for wanted_rank in [8, 4, 3, 1, 2, ]:
        for fqname in keys:
            rank = matches[fqname]
            if rank == wanted_rank:
                fq_names.append(fqname)
    return render_template("link_list_item_panel.html",
                           headline=_("Items with similar names to '%(item_name)s'", item_name=shorten_item_id(item_name)),
                           item=item,
                           item_name=item_name,  # XXX no item
                           fqname=split_fqname(item_name),
                           fq_names=fq_names)


def findMatches(fq_name, s_re=None, e_re=None):
    """ Find similar item names.

    :param fq_name: fqname to match
    :param s_re: start re for wiki matching
    :param e_re: end re for wiki matching
    :rtype: tuple
    :returns: start word, end word, matches dict
    """

    fq_names = [fqname for rev in flaskg.storage.documents(wikiname=app.cfg.interwikiname) for fqname in rev.fqnames
                if rev.fqname is not None]
    if fq_name in fq_names:
        fq_names.remove(fq_name)
    # Get matches using wiki way, start and end of word
    start, end, matches = wikiMatches(fq_name, fq_names, start_re=s_re, end_re=e_re)
    # Get the best 10 close matches
    close_matches = {}
    found = 0
    for fqname in closeMatches(fq_name, fq_names):
        if fqname not in matches:
            # Skip fqname already in matches
            close_matches[fqname] = 8
            found += 1
            # Stop after 10 matches
            if found == 10:
                break
    # Finally, merge both dicts
    matches.update(close_matches)
    return start, end, matches


def wikiMatches(fq_name, fq_names, start_re=None, end_re=None):
    """
    Get fqnames that starts or ends with same word as this fq_name.

    Matches are ranked like this:
        4 - item is subitem of fq_name
        3 - match both start and end
        2 - match end
        1 - match start

    :param fq_name: fqname to match
    :param fq_names: list of fqnames
    :param start_re: start word re (compile regex)
    :param end_re: end word re (compile regex)
    :rtype: tuple
    :returns: start, end, matches dict
    """
    if start_re is None:
        start_re = re.compile(u'([{0}][{1}]+)'.format(CHARS_UPPER, CHARS_LOWER))
    if end_re is None:
        end_re = re.compile(u'([{0}][{1}]+)$'.format(CHARS_UPPER, CHARS_LOWER))

    # If we don't get results with wiki words matching, fall back to
    # simple first word and last word, using spaces.
    item_name = fq_name.value
    words = item_name.split()
    match = start_re.match(item_name)
    if match:
        start = match.group(1)
    else:
        start = words[0]

    match = end_re.search(item_name)
    if match:
        end = match.group(1)
    else:
        end = words[-1]

    matches = {}
    subitem = item_name + '/'

    # Find any matching item names and rank by type of match
    for fqname in fq_names:
        name = fqname.value
        if name.startswith(subitem):
            matches[fqname] = 4
        else:
            if name.startswith(start):
                matches[fqname] = 1
            if name.endswith(end):
                matches[fqname] = matches.get(name, 0) + 2

    return start, end, matches


def closeMatches(fq_name, fq_names):
    """ Get close matches.

    Return all matching fqnames with rank above cutoff value.

    :param fq_name: fqname to match
    :param fq_names: list of fqnames
    :rtype: list
    :returns: list of matching item names, sorted by rank
    """
    if not fq_names:
        return []
    # Match using case insensitive matching
    # Make mapping from lower item names to fqnames.
    lower = {}
    for fqname in fq_names:
        name = fqname.value
        key = name.lower()
        if key in lower:
            lower[key].append(fqname)
        else:
            lower[key] = [fqname]
    # Get all close matches
    item_name = fq_name.value
    all_matches = difflib.get_close_matches(item_name.lower(), lower.keys(),
                                            n=len(lower), cutoff=0.6)

    # Replace lower names with original names
    matches = []
    for name in all_matches:
        matches.extend(lower[name])

    return matches


@frontend.route('/+sitemap/<itemname:item_name>')
def sitemap(item_name):
    """
    sitemap view shows item link structure, relative to current item
    """
    fq_name = split_fqname(item_name)
    try:
        item = Item.create(item_name)
    except AccessDenied:
        abort(403)
    if isinstance(item, NonExistent):
        abort(404, item_name)

    backrefs = NestedItemListBuilder().recurse_build([fq_name], backrefs=True)
    del backrefs[0]  # don't show current item name as sole toplevel list item
    sitemap = NestedItemListBuilder().recurse_build([fq_name])
    del sitemap[0]  # don't show current item name as sole toplevel list item
    return render_template('sitemap.html',
                           item=item,
                           item_name=item_name,
                           backrefs=backrefs,
                           sitemap=sitemap,
                           fqname=fq_name,
    )


class NestedItemListBuilder(object):
    def __init__(self):
        self.children = set()
        self.numnodes = 0
        self.maxnodes = 35  # approx. max count of nodes, not strict

    def recurse_build(self, fq_names, backrefs=False):
        result = []
        if self.numnodes < self.maxnodes:
            for fq_name in fq_names:
                self.children.add(fq_name)
                result.append(fq_name)
                self.numnodes += 1
                childs = self.childs(fq_name, backrefs=backrefs)
                if childs:
                    childs = self.recurse_build(childs, backrefs=backrefs)
                    result.append(childs)
        return result

    def childs(self, fq_name, backrefs=False):
        # does not recurse
        try:
            item = flaskg.storage.get_item(**fq_name.query)
            rev = item[CURRENT]
        except (AccessDenied, KeyError):
            return []
        if backrefs:
            itemlinks = _backrefs(fq_name.value)
        else:
            itemlinks = set(split_fqname_list(rev.meta.get(ITEMLINKS, []) + rev.meta.get(ITEMTRANSCLUSIONS, [])))
        return [child for child in itemlinks if self.is_ok(child)]

    def is_ok(self, child):
        if child not in self.children:
            if not flaskg.user.may.read(child):
                return False
            if flaskg.storage.get_item(**child.query):
                self.children.add(child)
                return True
        return False


@frontend.route('/+tags', defaults=dict(namespace=NAMESPACE_DEFAULT), methods=['GET'])
@frontend.route('/<namespace>/+tags')
def global_tags(namespace):
    """
    Show a list or tag cloud of tags in this wiki.

    If namespace == 'all' tags from all namespaces are shown.
    If namespace == '' tags from the default namespace are shown.
    If namespace == '<namespace>' tags from that namespace are shown.
    """
    title_name = _(u'Global Tags')
    query = {WIKINAME: app.cfg.interwikiname}
    fqname = CompositeName(NAMESPACE_ALL, NAME_EXACT, u'')
    if namespace != NAMESPACE_ALL:
        query[NAMESPACE] = namespace
        fqname = split_fqname(namespace)
    if namespace == NAMESPACE_DEFAULT:
        headline = _("Global Tags")
    elif namespace == NAMESPACE_ALL:
        headline = _("Global Tags in All Namespaces")
    else:
        headline = _("Tags in Namespace '%(namespace)s'", namespace=namespace)
    revs = flaskg.storage.documents(**query)
    tags_counts = {}
    for rev in revs:
        tags = rev.meta.get(TAGS, [])
        logging.debug("name {0!r} rev {1} tags {2!r}".format(rev.name, rev.meta[REVID], tags))
        for tag in tags:
            tags_counts[tag] = tags_counts.setdefault(tag, 0) + 1
    tags_counts = sorted(tags_counts.items())
    if tags_counts:
        # this is a simple linear scaling
        counts = [count for tags, count in tags_counts]
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
            return "weight{0}".format(int(weight))  # weight0, ..., weight9
        tags = [(cls(count), tag) for tag, count in tags_counts]
    else:
        tags = []
    return render_template("global_tags.html",
                           headline=headline,
                           title_name=title_name,
                           fqname=fqname,
                           tags=tags)


@frontend.route('/+tags/<itemname:tag>', defaults=dict(namespace=NAMESPACE_DEFAULT), methods=['GET'])
@frontend.route('/<namespace>/+tags/<itemname:tag>')
def tagged_items(tag, namespace):
    """
    show all items' names that have tag <tag> and belong to namespace <namespace>
    """
    terms = And([Term(WIKINAME, app.cfg.interwikiname), Term(TAGS, tag), ])
    if namespace != NAMESPACE_ALL:
        terms = And([terms, Term(NAMESPACE, namespace), ])
    query = And(terms)
    revs = flaskg.storage.search(query, limit=None)
    fq_names = [fq_name for rev in revs for fq_name in rev.fqnames]
    return render_template("link_list_no_item_panel.html",
                           headline=_("Items tagged with %(tag)s", tag=tag),
                           item_name=tag,
                           fq_names=fq_names)


@frontend.route('/+template/<path:filename>')
def template(filename):
    """
    serve a rendered template from <filename>

    used for (but not limited to) translation of javascript / css / html
    """
    content = render_template(filename)
    ct, enc = mimetypes.guess_type(filename)
    response = make_response((content, 200, {'content-type': ct or 'text/plain;charset=utf-8'}))
    if ct in ['application/javascript', 'text/css', 'text/html', ]:
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


@frontend.route('/+tickets', methods=['GET', 'POST'])
def tickets():
    """
    Show a list of ticket items
    """
    if request.method == 'POST':
        query = request.form['q']
        status = request.form['status']
    else:
        query = None
        status = u'open'

    current_timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    idx_name = ALL_REVS
    qp = flaskg.storage.query_parser([TAGS, SUMMARY, CONTENT, ITEMID], idx_name=idx_name)
    term1 = [Term(ITEMTYPE, ITEMTYPE_TICKET)]
    term2 = []
    if query:
        term2.append(qp.parse(query))

    if status == u'open':
        term1.append(Term(CLOSED, False))
    elif status == u'closed':
        term1.append(Term(CLOSED, True))

    selected_tags = set(request.args.getlist(u'selected_tags'))
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
        # E.g of link for second case is  +tickets?assigned_to=username
        # for first case i.e while we are using search box, variable 'query' (i.e what ever is searched)  should be present either in
        # TAGS, SUMMARY, CONTENT, ITEMID 'or' ASSIGNED_TO 'and' should be of given status (closed or open).
        # while in second case we have to get all the results having given status 'and' Assigned_to =  request.args.get(ASSIGNED_TO).
        # first case we use 'and'  while in second case we use 'or' while adding the assigned_to condition to retrieve the results.
        if query:
            term2 = Or(term2)
            term1.extend([term2])
        else:
            term1.extend(term2)
        q = And(term1)
        results = searcher.search(q, limit=None)
        tags = get_itemtype_specific_tags(ITEMTYPE_TICKET)
        return render_template('tickets.html',
                               results=results,
                               query=query,
                               status=status,
                               tags=tags,
                               selected_tags=selected_tags,
                               current_timestamp=current_timestamp,
        )


@frontend.route('/+tickets/query', methods=['GET', 'POST'])
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
        if request.method == 'POST':
            effort = request.form.get('effort')
            difficulty = request.form.get('difficulty')
            severity = request.form.get('severity')
            priority = request.form.get('priority')
            tags = request.form.get('tags')
            assigned_to = request.form.get('assigned_to')
            author = request.form.get('author')
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

        return render_template('ticket/advanced.html',
                               search_form=form,
                               ticket_results=results,
                               suggested_tags=suggested_tags,
                               timestamp=datetime.fromtimestamp,
                               is_ticket=True,
                               )


@frontend.route('/+comment', defaults=dict(item_name=u''), methods=['POST'])
def comment(item_name):
    """
    Initiated by tickets.js when user clicks Save button adding a reply to a prior comment.

    An html fragment formatting a new comment is produced. It is inserted into the page via javascript.
    """
    itemid = request.form.get('refers_to')
    reply_to = request.form.get('reply_to')
    data = request.form.get('data')
    if data:
        current_timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        item_name = unicode(itemid) + u'/' + u'comment_' + unicode(current_timestamp)
        item = Item.create(item_name)
        item.modify({}, data=data, element=u'comment', contenttype_guessed=u'text/x.moin.wiki;charset=utf-8',
                    refers_to=itemid, reply_to=reply_to, author=flaskg.user.name[0])
        item = Item.create(item.name, rev_id=CURRENT)
        html = render_template('ticket/comment.html',
                               comment=item,
                               render_comment_data=render_comment_data,
                               datetime=datetime,
                               )
        return html


@frontend.route('/+new', methods=['GET', 'POST'])
def new():
    # TODO: Implement creation of blog entries and ticket items
    raise NotImplementedError


@frontend.errorhandler(404)
def page_not_found(e):
    return render_template('404.html',
                           path=request.path,
                           item_name=e.description), 404
