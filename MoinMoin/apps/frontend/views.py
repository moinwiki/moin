# Copyright: 2003-2010 MoinMoin:ThomasWaldmann
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
from datetime import datetime
from itertools import chain
from collections import namedtuple, OrderedDict
try:
    import json
except ImportError:
    import simplejson as json

from flask import request, url_for, flash, Response, redirect, session, abort, jsonify
from flask import current_app as app
from flask import g as flaskg
from flaskext.babel import format_date
from flaskext.themes import get_themes_list

from flatland import Form, String, Integer, Boolean, Enum
from flatland.validation import Validator, Present, IsEmail, ValueBetween, URLValidator, Converted, ValueAtLeast

from jinja2 import Markup

import pytz
from babel import Locale

from whoosh.query import Term, And, Or, DateRange

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.i18n import _, L_, N_
from MoinMoin.themes import render_template, get_editor_info, contenttype_to_class
from MoinMoin.apps.frontend import frontend
from MoinMoin.items import Item, NonExistent
from MoinMoin.items import ROWS_META, COLS, ROWS_DATA
from MoinMoin import config, user, util, wikiutil
from MoinMoin.config import ACTION, COMMENT, WIKINAME, CONTENTTYPE, ITEMLINKS, ITEMTRANSCLUSIONS, NAME, NAME_EXACT, \
                            CONTENTTYPE_GROUPS, MTIME, TAGS, ITEMID, REVID, CURRENT, CONTENT
from MoinMoin.util import crypto
from MoinMoin.util.interwiki import url_for_item
from MoinMoin.security.textcha import TextCha, TextChaizedForm, TextChaValid
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, AccessDeniedError
from MoinMoin.signalling import item_displayed, item_modified


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
    item_name = app.cfg.item_root
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
Disallow: /+copy/
Disallow: /+content/
Disallow: /+delete/
Disallow: /+ajaxdelete/
Disallow: /+ajaxdestroy/
Disallow: /+ajaxmodify/
Disallow: /+destroy/
Disallow: /+rename/
Disallow: /+revert/
Disallow: /+index/
Disallow: /+jfu-server/
Disallow: /+sitemap/
Disallow: /+similar_names/
Disallow: /+quicklink/
Disallow: /+subscribe/
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


class ValidSearch(Validator):
    """Validator for a valid search form
    """
    too_short_query_msg = L_('Search query too short.')

    def validate(self, element, state):
        if element['q'].value is None:
            # no query, nothing to search for
            return False
        if len(element['q'].value) < 2:
            return self.note_error(element, state, 'too_short_query_msg')
        return True

class SearchForm(Form):
    q = String.using(optional=False, default=u'').with_properties(autofocus=True, placeholder=L_("Search Query"))
    history = Boolean.using(label=L_('search also in non-current revisions'), optional=True)
    submit = String.using(default=L_('Search'), optional=True)

    validators = [ValidSearch()]


@frontend.route('/+search', methods=['GET', 'POST'])
def search():
    search_form = SearchForm.from_flat(request.values)
    valid = search_form.validate()
    search_form['submit'].set_default() # XXX from_flat() kills all values
    query = search_form['q'].value
    if valid:
        history = bool(request.values.get('history'))
        qp = flaskg.storage.query_parser([NAME_EXACT, NAME, CONTENT], all_revs=history)
        q = qp.parse(query)
        with flaskg.storage.get_index(all_revs=history).searcher() as searcher:
            flaskg.clock.start('search')
            results = searcher.search(q, limit=100)
            flaskg.clock.stop('search')
            # XXX if found that calling key_terms like you see below is 1000..10000x
            # slower than the search itself, so we better don't do that right now.
            key_terms_is_fast = False
            if key_terms_is_fast:
                flaskg.clock.start('search suggestions')
                name_suggestions = u', '.join([word for word, score in results.key_terms(NAME, docs=20, numterms=10)])
                content_suggestions = u', '.join([word for word, score in results.key_terms(CONTENT, docs=20, numterms=10)])
                flaskg.clock.stop('search suggestions')
            else:
                name_suggestions = u''
                content_suggestions = u''
            flaskg.clock.start('search render')
            html = render_template('search.html',
                                   results=results,
                                   name_suggestions=name_suggestions,
                                   content_suggestions=content_suggestions,
                                   query=query,
                                   medium_search_form=search_form,
                                   item_name='+search', # XXX
                                  )
            flaskg.clock.stop('search render')
    else:
        html = render_template('search.html',
                               query=query,
                               medium_search_form=search_form,
                               item_name='+search', # XXX
                              )
    return html


@frontend.route('/<itemname:item_name>', defaults=dict(rev=CURRENT), methods=['GET'])
@frontend.route('/+show/<rev>/<itemname:item_name>', methods=['GET'])
def show_item(item_name, rev):
    flaskg.user.addTrail(item_name)
    item_displayed.send(app._get_current_object(),
                        item_name=item_name)
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDeniedError:
        abort(403)
    show_revision = rev != CURRENT
    show_navigation = False # TODO
    first_rev = last_rev = None # TODO
    if isinstance(item, NonExistent):
        status = 404
    else:
        status = 200
    content = render_template('show.html',
                              item=item, item_name=item.name,
                              rev=item.rev,
                              contenttype=item.contenttype,
                              first_rev_id=first_rev,
                              last_rev_id=last_rev,
                              data_rendered=Markup(item._render_data()),
                              show_revision=show_revision,
                              show_navigation=show_navigation,
                              search_form=SearchForm.from_defaults(),
                             )
    return Response(content, status)


@frontend.route('/+show/<itemname:item_name>')
def redirect_show_item(item_name):
    return redirect(url_for_item(item_name))


@frontend.route('/+dom/<rev>/<itemname:item_name>')
@frontend.route('/+dom/<itemname:item_name>', defaults=dict(rev=CURRENT))
def show_dom(item_name, rev):
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDeniedError:
        abort(403)
    if isinstance(item, NonExistent):
        status = 404
    else:
        status = 200
    content = render_template('dom.xml',
                              data_xml=Markup(item._render_data_xml()),
                             )
    return Response(content, status, mimetype='text/xml')


# XXX this is just a temporary view to test the indexing converter
@frontend.route('/+indexable/<rev>/<itemname:item_name>')
@frontend.route('/+indexable/<itemname:item_name>', defaults=dict(rev=CURRENT))
def indexable(item_name, rev):
    from MoinMoin.storage.middleware.indexing import convert_to_indexable
    item = flaskg.storage[item_name]
    rev = item[rev]
    content = convert_to_indexable(rev.meta, rev.data)
    return Response(content, 200, mimetype='text/plain')


@frontend.route('/+highlight/<rev>/<itemname:item_name>')
@frontend.route('/+highlight/<itemname:item_name>', defaults=dict(rev=CURRENT))
def highlight_item(item_name, rev):
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDeniedError:
        abort(403)
    return render_template('highlight.html',
                           item=item, item_name=item.name,
                           data_text=Markup(item._render_data_highlight()),
                          )


@frontend.route('/+meta/<itemname:item_name>', defaults=dict(rev=CURRENT))
@frontend.route('/+meta/<rev>/<itemname:item_name>')
def show_item_meta(item_name, rev):
    flaskg.user.addTrail(item_name)
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDeniedError:
        abort(403)
    show_revision = show_navigation = rev != CURRENT
    first_rev = None
    last_rev = None
    if show_navigation:
        rev_ids = list(item.rev.item.iter_revs())
        if rev_ids:
            first_rev = rev_ids[0]
            last_rev = rev_ids[-1]
    return render_template('meta.html',
                           item=item, item_name=item.name,
                           rev=item.rev,
                           contenttype=item.contenttype,
                           first_rev_id=first_rev,
                           last_rev_id=last_rev,
                           meta_rendered=Markup(item._render_meta()),
                           show_revision=show_revision,
                           show_navigation=show_navigation,
                          )

@frontend.route('/+content/<rev>/<itemname:item_name>')
@frontend.route('/+content/<itemname:item_name>', defaults=dict(rev=CURRENT))
def content_item(item_name, rev):
    """ same as show_item, but we only show the content """
    # first check whether we have a valid search query:
    search_form = SearchForm.from_flat(request.values)
    if search_form.validate():
        return _search(search_form, item_name)
    search_form['submit'].set_default() # XXX from_flat() kills all values
    item_displayed.send(app._get_current_object(),
                        item_name=item_name)
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDeniedError:
        abort(403)
    return render_template('content.html',
                           item_name=item.name,
                           data_rendered=Markup(item._render_data()),
                           )

@frontend.route('/+get/<rev>/<itemname:item_name>')
@frontend.route('/+get/<itemname:item_name>', defaults=dict(rev=CURRENT))
def get_item(item_name, rev):
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDeniedError:
        abort(403)
    return item.do_get()

@frontend.route('/+download/<rev>/<itemname:item_name>')
@frontend.route('/+download/<itemname:item_name>', defaults=dict(rev=CURRENT))
def download_item(item_name, rev):
    try:
        item = Item.create(item_name, rev_id=rev)
        mimetype = request.values.get("mimetype")
    except AccessDeniedError:
        abort(403)
    return item.do_get(force_attachment=True, mimetype=mimetype)

@frontend.route('/+convert/<itemname:item_name>')
def convert_item(item_name):
    """
    return a converted item.

    We create two items : the original one, and an empty
    one with the expected mimetype for the converted item.

    To get the converted item, we just feed his converter,
    with the internal representation of the item.
    """
    contenttype = request.values.get('contenttype')
    try:
        item = Item.create(item_name, rev_id=CURRENT)
    except AccessDeniedError:
        abort(403)
    # We don't care about the name of the converted object
    # It should just be a name which does not exist.
    # XXX Maybe use a random name to be sure it does not exist
    item_name_converted = item_name + 'converted'
    try:
        converted_item = Item.create(item_name_converted, contenttype=contenttype)
    except AccessDeniedError:
        abort(403)
    return converted_item._convert(item.internal_representation())


@frontend.route('/+modify/<itemname:item_name>', methods=['GET', 'POST'])
def modify_item(item_name):
    """Modify the wiki item item_name.

    On GET, displays a form.
    On POST, saves the new page (unless there's an error in input).
    After successful POST, redirects to the page.
    """
    contenttype = request.values.get('contenttype')
    template_name = request.values.get('template')
    try:
        item = Item.create(item_name, contenttype=contenttype)
    except AccessDeniedError:
        abort(403)
    if not flaskg.user.may.write(item_name):
        abort(403)
    return item.do_modify(contenttype, template_name)


class CommentForm(TextChaizedForm):
    comment = String.using(label=L_('Comment'), optional=True).with_properties(placeholder=L_("Comment about your change"))
    submit = String.using(default=L_('OK'), optional=True)

class TargetCommentForm(CommentForm):
    target = String.using(label=L_('Target')).with_properties(placeholder=L_("The name of the target item")).validated_by(Present())

class RevertItemForm(CommentForm):
    name = 'revert_item'

class DeleteItemForm(CommentForm):
    name = 'delete_item'

class DestroyItemForm(CommentForm):
    name = 'destroy_item'

class CopyItemForm(TargetCommentForm):
    name = 'copy_item'

class RenameItemForm(TargetCommentForm):
    name = 'rename_item'

class ContenttypeFilterForm(Form):
    name = 'contenttype_filter'
    markup_text_items = Boolean.using(label=L_('markup text'), optional=True, default=1)
    other_text_items = Boolean.using(label=L_('other text'), optional=True, default=1)
    image_items = Boolean.using(label=L_('image'), optional=True, default=1)
    audio_items = Boolean.using(label=L_('audio'), optional=True, default=1)
    video_items = Boolean.using(label=L_('video'), optional=True, default=1)
    other_items = Boolean.using(label=L_('other'), optional=True, default=1)
    unknown_items = Boolean.using(label=L_('unknown'), optional=True, default=1)
    submit = String.using(default=L_('Filter'), optional=True)


@frontend.route('/+revert/<rev>/<itemname:item_name>', methods=['GET', 'POST'])
def revert_item(item_name, rev):
    try:
        item = Item.create(item_name, rev_id=rev)
    except AccessDeniedError:
        abort(403)
    if request.method == 'GET':
        form = RevertItemForm.from_defaults()
        TextCha(form).amend_form()
    elif request.method == 'POST':
        form = RevertItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        if form.validate():
            item.revert()
            return redirect(url_for_item(item_name))
    return render_template(item.revert_template,
                           item=item, item_name=item_name,
                           rev_id=rev,
                           form=form,
                          )


@frontend.route('/+copy/<itemname:item_name>', methods=['GET', 'POST'])
def copy_item(item_name):
    try:
        item = Item.create(item_name)
    except AccessDeniedError:
        abort(403)
    if request.method == 'GET':
        form = CopyItemForm.from_defaults()
        TextCha(form).amend_form()
        form['target'] = item.name
    elif request.method == 'POST':
        form = CopyItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        if form.validate():
            target = form['target'].value
            comment = form['comment'].value
            item.copy(target, comment)
            return redirect(url_for_item(target))
    return render_template(item.copy_template,
                           item=item, item_name=item_name,
                           form=form,
                          )


@frontend.route('/+rename/<itemname:item_name>', methods=['GET', 'POST'])
def rename_item(item_name):
    try:
        item = Item.create(item_name)
    except AccessDeniedError:
        abort(403)
    if request.method == 'GET':
        form = RenameItemForm.from_defaults()
        TextCha(form).amend_form()
        form['target'] = item.name
    elif request.method == 'POST':
        form = RenameItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        if form.validate():
            target = form['target'].value
            comment = form['comment'].value
            item.rename(target, comment)
            return redirect(url_for_item(target))
    return render_template(item.rename_template,
                           item=item, item_name=item_name,
                           form=form,
                          )


@frontend.route('/+delete/<itemname:item_name>', methods=['GET', 'POST'])
def delete_item(item_name):
    try:
        item = Item.create(item_name)
    except AccessDeniedError:
        abort(403)
    if request.method == 'GET':
        form = DeleteItemForm.from_defaults()
        TextCha(form).amend_form()
    elif request.method == 'POST':
        form = DeleteItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        if form.validate():
            comment = form['comment'].value
            item.delete(comment)
            return redirect(url_for_item(item_name))
    return render_template(item.delete_template,
                           item=item, item_name=item_name,
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
            except AccessDeniedError:
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
            except AccessDeniedError:
                response["status"].append(False)

    return jsonify(response)


@frontend.route('/+ajaxmodify/<itemname:item_name>', methods=['POST'])
@frontend.route('/+ajaxmodify', methods=['POST'], defaults=dict(item_name=''))
def ajaxmodify(item_name):
    newitem = request.values.get("newitem")
    if not newitem:
        abort(404)
    if item_name:
        newitem = item_name + u'/' + newitem

    return redirect(url_for('.modify_item', item_name=newitem))


@frontend.route('/+destroy/<rev>/<itemname:item_name>', methods=['GET', 'POST'])
@frontend.route('/+destroy/<itemname:item_name>', methods=['GET', 'POST'], defaults=dict(rev=None))
def destroy_item(item_name, rev):
    if rev is None:
        # no revision given
        _rev = CURRENT # for item creation
        destroy_item = True
    else:
        _rev = rev
        destroy_item = False
    try:
        item = Item.create(item_name, rev_id=_rev)
    except AccessDeniedError:
        abort(403)
    if request.method == 'GET':
        form = DestroyItemForm.from_defaults()
        TextCha(form).amend_form()
    elif request.method == 'POST':
        form = DestroyItemForm.from_flat(request.form)
        TextCha(form).amend_form()
        if form.validate():
            comment = form['comment'].value
            item.destroy(comment=comment, destroy_item=destroy_item)
            return redirect(url_for_item(item_name))
    return render_template(item.destroy_template,
                           item=item, item_name=item_name,
                           rev_id=rev,
                           form=form,
                          )


@frontend.route('/+jfu-server/<itemname:item_name>', methods=['POST'])
@frontend.route('/+jfu-server', defaults=dict(item_name=''), methods=['POST'])
def jfu_server(item_name):
    """jquery-file-upload server component
    """
    data_file = request.files.get('data_file')
    subitem_name = data_file.filename
    contenttype = data_file.content_type # guess by browser, based on file name
    if item_name:
        subitem_prefix = item_name + u'/'
    else:
        subitem_prefix = u''
    item_name = subitem_prefix + subitem_name
    try:
        item = Item.create(item_name)
        revid, size = item.modify()
        item_modified.send(app._get_current_object(),
                           item_name=item_name)
        return jsonify(name=subitem_name,
                       size=size,
                       url=url_for('.show_item', item_name=item_name, rev=revid),
                       contenttype=contenttype_to_class(contenttype),
                      )
    except AccessDeniedError:
        abort(403)


@frontend.route('/+index/', defaults=dict(item_name=''), methods=['GET', 'POST'])
@frontend.route('/+index/<itemname:item_name>', methods=['GET', 'POST'])
def index(item_name):
    try:
        item = Item.create(item_name) # when item_name='', it gives toplevel index
    except AccessDeniedError:
        abort(403)

    if request.method == 'GET':
        form = ContenttypeFilterForm.from_defaults()
        selected_groups = None
    elif request.method == "POST":
        form = ContenttypeFilterForm.from_flat(request.form)
        selected_groups = [gname.replace("_", " ") for gname, value in form.iteritems()
                           if form[gname].value]
        if u'submit' in selected_groups:
            selected_groups.remove(u'submit')
        if not selected_groups:
            form = ContenttypeFilterForm.from_defaults()

    startswith = request.values.get("startswith")
    index = item.flat_index(startswith, selected_groups)

    ct_groups = [(gname, ", ".join([ctlabel for ctname, ctlabel in contenttypes]))
                 for gname, contenttypes in CONTENTTYPE_GROUPS]
    ct_groups = dict(ct_groups)

    initials = item.name_initial(item.flat_index())
    initials = [initial.upper() for initial in initials]
    initials = list(set(initials))
    initials = sorted(initials)
    detailed_index = item.get_detailed_index(index)
    detailed_index = sorted(detailed_index, key=lambda name: name[0].lower())

    item_names = item_name.split(u'/')
    return render_template(item.index_template,
                           item_name=item_name,
                           item_names=item_names,
                           index=detailed_index,
                           initials=initials,
                           startswith=startswith,
                           contenttype_groups=ct_groups,
                           form=form,
                          )


@frontend.route('/+backrefs/<itemname:item_name>')
def backrefs(item_name):
    """
    Returns the list of all items that link or transclude item_name

    :param item_name: the name of the current item
    :type item_name: unicode
    :returns: a page with all the items which link or transclude item_name
    """
    refs_here = _backrefs(item_name)
    return render_template('item_link_list.html',
                           item_name=item_name,
                           headline=_(u'Refers Here'),
                           item_names=refs_here
                          )


def _backrefs(item_name):
    """
    Returns a list with all names of items which ref item_name

    :param item_name: the name of the item transcluded or linked
    :type item_name: unicode
    :returns: the list of all items which ref item_name
    """
    q = And([Term(WIKINAME, app.cfg.interwikiname),
             Or([Term(ITEMTRANSCLUSIONS, item_name), Term(ITEMLINKS, item_name)])])
    revs = flaskg.storage.search(q, all_revs=False)
    return [rev.meta[NAME] for rev in revs]


@frontend.route('/+history/<itemname:item_name>')
def history(item_name):
    offset = request.values.get('offset', 0)
    offset = max(int(offset), 0)
    bookmark_time = int(request.values.get('bookmark', 0))
    if flaskg.user.valid:
        results_per_page = flaskg.user.results_per_page
    else:
        results_per_page = app.cfg.results_per_page
    terms = [Term(WIKINAME, app.cfg.interwikiname), Term(NAME_EXACT, item_name), ]
    if bookmark_time:
        terms.append(DateRange(MTIME, start=datetime.utcfromtimestamp(bookmark_time), end=None))
    query = And(terms)
    # TODO: due to how getPageContent and the template works, we need to use limit=None -
    # it would be better to use search_page (and an appropriate limit, if needed)
    revs = flaskg.storage.search(query, all_revs=True, sortedby=[MTIME], reverse=True, limit=None)
    # get rid of the content value to save potentially big amounts of memory:
    history = [dict((k, v) for k, v in rev.meta.iteritems() if k != CONTENT) for rev in revs]
    history_page = util.getPageContent(history, offset, results_per_page)
    return render_template('history.html',
                           item_name=item_name, # XXX no item here
                           history_page=history_page,
                           bookmark_time=bookmark_time,
                          )


@frontend.route('/+history')
def global_history():
    all_revs = bool(request.values.get('all'))
    if flaskg.user.valid:
        bookmark_time = flaskg.user.getBookmark()
    else:
        bookmark_time = None
    query = Term(WIKINAME, app.cfg.interwikiname)
    if bookmark_time is not None:
        query = And([query, DateRange(MTIME, start=datetime.utcfromtimestamp(bookmark_time), end=None)])
    revs = flaskg.storage.search(query, all_revs=all_revs, sortedby=[MTIME], reverse=True, limit=1000) # was: all_revs=False
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

    item_name = request.values.get('item_name', '') # actions menu puts it into qs
    current_timestamp = int(time.time())
    return render_template('global_history.html',
                           item_name=item_name, # XXX no item
                           history=history,
                           current_timestamp=current_timestamp,
                           bookmark_time=bookmark_time,
                          )

def _compute_item_sets():
    """
    compute sets of existing, linked, transcluded and no-revision item names
    """
    linked = set()
    transcluded = set()
    existing = set()
    revs = flaskg.storage.documents(all_revs=False, wikiname=app.cfg.interwikiname)
    for rev in revs:
        existing.add(rev.meta[NAME])
        linked.update(rev.meta.get(ITEMLINKS, []))
        transcluded.update(rev.meta.get(ITEMTRANSCLUSIONS, []))
    return existing, linked, transcluded


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
    item_name = request.values.get('item_name', '') # actions menu puts it into qs
    return render_template('item_link_list.html',
                           headline=_(u'Wanted Items'),
                           item_name=item_name,
                           item_names=wanteds)


@frontend.route('/+orphans')
def orphaned_items():
    """
    Return a list view of existing items not being linked or transcluded
    by any other item (which makes them sometimes not discoverable).
    """
    existing, linked, transcluded = _compute_item_sets()
    referred = linked | transcluded
    orphans = existing - referred
    item_name = request.values.get('item_name', '') # actions menu puts it into qs
    return render_template('item_link_list.html',
                           item_name=item_name,
                           headline=_(u'Orphaned Items'),
                           item_names=orphans)


@frontend.route('/+quicklink/<itemname:item_name>')
def quicklink_item(item_name):
    """ Add/Remove the current wiki page to/from the user quicklinks """
    u = flaskg.user
    msg = None
    if not u.valid:
        msg = _("You must login to use this action: %(action)s.", action="quicklink/quickunlink"), "error"
    elif not flaskg.user.isQuickLinkedTo([item_name]):
        if not u.addQuicklink(item_name):
            msg = _('A quicklink to this page could not be added for you.'), "error"
    else:
        if not u.removeQuicklink(item_name):
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
    if not u.valid:
        msg = _("You must login to use this action: %(action)s.", action="subscribe/unsubscribe"), "error"
    elif not u.may.read(item_name):
        msg = _("You are not allowed to subscribe to an item you may not read."), "error"
    elif u.isSubscribedTo([item_name]):
        # Try to unsubscribe
        if not u.unsubscribe(item_name):
            msg = _("Can't remove regular expression subscription!") + u' ' + \
                  _("Edit the subscription regular expressions in your settings."), "error"
    else:
        # Try to subscribe
        if not u.subscribe(item_name):
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

    username = String.using(label=L_('Name')).with_properties(placeholder=L_("The login name you want to use")).validated_by(Present())
    password1 = String.using(label=L_('Password')).with_properties(placeholder=L_("The login password you want to use")).validated_by(Present())
    password2 = String.using(label=L_('Password')).with_properties(placeholder=L_("Repeat the same password")).validated_by(Present())
    email = String.using(label=L_('E-Mail')).with_properties(placeholder=L_("Your E-Mail address")).validated_by(IsEmail())
    openid = String.using(label=L_('OpenID'), optional=True).with_properties(placeholder=L_("Your OpenID address")).validated_by(URLValidator())
    submit = String.using(default=L_('Register'), optional=True)

    validators = [ValidRegistration()]


class OpenIDForm(TextChaizedForm):
    """
    OpenID registration form, inherited from the simple registration form.
    """
    name = 'openid'

    username = String.using(label=L_('Name')).with_properties(placeholder=L_("The login name you want to use")).validated_by(Present())
    password1 = String.using(label=L_('Password')).with_properties(placeholder=L_("The login password you want to use")).validated_by(Present())
    password2 = String.using(label=L_('Password')).with_properties(placeholder=L_("Repeat the same password")).validated_by(Present())

    email = String.using(label=L_('E-Mail')).with_properties(placeholder=L_("Your E-Mail address")).validated_by(IsEmail())
    openid = String.using(label=L_('OpenID')).with_properties(placeholder=L_("Your OpenID address")).validated_by(URLValidator())
    submit = String.using(optional=True)

    validators = [ValidRegistration()]

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
    item_name = 'Register' # XXX
    # is openid_submit in the form?
    isOpenID = 'openid_submit' in request.values

    if isOpenID:
        # this is an openid continuation
        if not _using_openid_auth():
            return Response('No OpenIDAuth in auth list', 403)

        template = 'openid_register.html'
        if request.method == 'GET':
            form = OpenIDForm.from_defaults()
            # we got an openid from the multistage redirect
            oid = request.values.get('openid_openid')
            if oid:
                form['openid'] = oid
            TextCha(form).amend_form()

        elif request.method == 'POST':
            form = OpenIDForm.from_flat(request.form)
            TextCha(form).amend_form()

            if form.validate():
                msg = user.create_user(username=form['username'].value,
                                       password=form['password1'].value,
                                       email=form['email'].value,
                                       openid=form['openid'].value,
                                      )
                if msg:
                    flash(msg, "error")
                else:
                    flash(_('Account created, please log in now.'), "info")
                    return redirect(url_for('.show_root'))

    else:
        # not openid registration and no MoinAuth
        if not _using_moin_auth():
            return Response('No MoinAuth in auth list', 403)

        template = 'register.html'
        if request.method == 'GET':
            form = RegistrationForm.from_defaults()
            TextCha(form).amend_form()

        elif request.method == 'POST':
            form = RegistrationForm.from_flat(request.form)
            TextCha(form).amend_form()

            if form.validate():
                msg = user.create_user(username=form['username'].value,
                                       password=form['password1'].value,
                                       email=form['email'].value,
                                       openid=form['openid'].value,
                                      )
                if msg:
                    flash(msg, "error")
                else:
                    flash(_('Account created, please log in now.'), "info")
                    return redirect(url_for('.show_root'))

    return render_template(template,
                           item_name=item_name,
                           form=form,
                          )


class ValidLostPassword(Validator):
    """Validator for a valid lost password form
    """
    name_or_email_needed_msg = L_('Your user name or your email address is needed.')

    def validate(self, element, state):
        if not(element['username'].valid and element['username'].value
               or
               element['email'].valid and element['email'].value):
            return self.note_error(element, state, 'name_or_email_needed_msg')

        return True


class PasswordLostForm(Form):
    """a simple password lost form"""
    name = 'lostpass'

    username = String.using(label=L_('Name'), optional=True).with_properties(placeholder=L_("Your login name"))
    email = String.using(label=L_('E-Mail'), optional=True).with_properties(placeholder=L_("Your E-Mail address")).validated_by(IsEmail())
    submit = String.using(default=L_('Recover password'), optional=True)

    validators = [ValidLostPassword()]


@frontend.route('/+lostpass', methods=['GET', 'POST'])
def lostpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'LostPass' # XXX

    if not _using_moin_auth():
        return Response('No MoinAuth in auth list', 403)

    if request.method == 'GET':
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
                u = users and user.User(users[0][ITEMID])
            if u and u.valid:
                is_ok, msg = u.mailAccountData()
                if not is_ok:
                    flash(msg, "error")
            flash(_("If this account exists, you will be notified."), "info")
            return redirect(url_for('.show_root'))
    return render_template('lostpass.html',
                           item_name=item_name,
                           form=form,
                          )

class ValidPasswordRecovery(Validator):
    """Validator for a valid password recovery form
    """
    passwords_mismatch_msg = L_('The passwords do not match.')
    password_encoding_problem_msg = L_('New password is unacceptable, encoding trouble.')

    def validate(self, element, state):
        if element['password1'].value != element['password2'].value:
            return self.note_error(element, state, 'passwords_mismatch_msg')

        try:
            crypto.crypt_password(element['password1'].value)
        except UnicodeError:
            return self.note_error(element, state, 'password_encoding_problem_msg')

        return True

class PasswordRecoveryForm(Form):
    """a simple password recovery form"""
    name = 'recoverpass'

    username = String.using(label=L_('Name')).with_properties(placeholder=L_("Your login name")).validated_by(Present())
    token = String.using(label=L_('Recovery token')).with_properties(placeholder=L_("The recovery token that has been sent to you")).validated_by(Present())
    password1 = String.using(label=L_('New password')).with_properties(placeholder=L_("The login password you want to use")).validated_by(Present())
    password2 = String.using(label=L_('New password (repeat)')).with_properties(placeholder=L_("Repeat the same password")).validated_by(Present())
    submit = String.using(default=L_('Change password'), optional=True)

    validators = [ValidPasswordRecovery()]


@frontend.route('/+recoverpass', methods=['GET', 'POST'])
def recoverpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'RecoverPass' # XXX

    if not _using_moin_auth():
        return Response('No MoinAuth in auth list', 403)

    if request.method == 'GET':
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
                           item_name=item_name,
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

    username = String.using(label=L_('Name'), optional=False).with_properties(autofocus=True).validated_by(Present())
    password = String.using(label=L_('Password'), optional=False).validated_by(Present())
    openid = String.using(label=L_('OpenID'), optional=True).validated_by(Present(), URLValidator())

    # the submit hidden field
    submit = String.using(optional=True)

    validators = [ValidLogin()]


@frontend.route('/+login', methods=['GET', 'POST'])
def login():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'Login' # XXX

    # multistage return
    if flaskg._login_multistage_name == 'openid':
        return Response(flaskg._login_multistage, mimetype='text/html')

    if request.method == 'GET':
        form = LoginForm.from_defaults()
        for authmethod in app.cfg.auth:
            hint = authmethod.login_hint()
            if hint:
                flash(hint, "info")
    elif request.method == 'POST':
        form = LoginForm.from_flat(request.form)
        if form.validate():
            # we have a logged-in, valid user
            return redirect(url_for('.show_root'))
        # flash the error messages (if any)
        for msg in flaskg._login_messages:
            flash(msg, "error")
    return render_template('login.html',
                           item_name=item_name,
                           login_inputs=app.cfg.auth_login_inputs,
                           form=form,
                          )


@frontend.route('/+logout')
def logout():
    flash(_("You are now logged out."), "info")
    for key in ['user.itemid', 'user.auth_method', 'user.auth_attribs', ]:
        if key in session:
            del session[key]
    return redirect(url_for('.show_root'))


class ValidChangePass(Validator):
    """Validator for a valid password change
    """
    passwords_mismatch_msg = L_('The passwords do not match.')
    current_password_wrong_msg = L_('The current password was wrong.')
    password_encoding_problem_msg = L_('New password is unacceptable, encoding trouble.')

    def validate(self, element, state):
        if not (element['password_current'].valid and element['password1'].valid and element['password2'].valid):
            return False

        if not user.User(name=flaskg.user.name, password=element['password_current'].value).valid:
            return self.note_error(element, state, 'current_password_wrong_msg')

        if element['password1'].value != element['password2'].value:
            return self.note_error(element, state, 'passwords_mismatch_msg')

        try:
            crypto.crypt_password(element['password1'].value)
        except UnicodeError:
            return self.note_error(element, state, 'password_encoding_problem_msg')
        return True


class UserSettingsPasswordForm(Form):
    name = 'usersettings_password'
    password_current = String.using(label=L_('Current Password')).with_properties(placeholder=L_("Your current login password")).validated_by(Present())
    password1 = String.using(label=L_('New password')).with_properties(placeholder=L_("The login password you want to use")).validated_by(Present())
    password2 = String.using(label=L_('New password (repeat)')).with_properties(placeholder=L_("Repeat the same password")).validated_by(Present())
    submit = String.using(default=L_('Change password'), optional=True)
    validators = [ValidChangePass()]


class UserSettingsNotificationForm(Form):
    name = 'usersettings_notification'
    email = String.using(label=L_('E-Mail')).with_properties(placeholder=L_("Your E-Mail address")).validated_by(IsEmail())
    submit = String.using(default=L_('Save'), optional=True)


class UserSettingsNavigationForm(Form):
    name = 'usersettings_navigation'
    # TODO: find a good way to handle quicklinks here
    submit = String.using(default=L_('Save'), optional=True)


class UserSettingsOptionsForm(Form):
    # TODO: if the checkbox in the form is checked, we get key: u'1' in the
    # form data and all is fine. if it is not checked, the key is not present
    # in the form data and flatland assigns None to the attribute (not False).
    # If moin detects the None, it thinks this has not been set and uses its
    # builtin defaults (for some True, for some others False). Makes
    # edit_on_doubleclick malfunctioning (because its default is True).
    name = 'usersettings_options'
    mailto_author = Boolean.using(label=L_('Publish my email (not my wiki homepage) in author info'), optional=True)
    edit_on_doubleclick = Boolean.using(label=L_('Open editor on double click'), optional=True)
    show_comments = Boolean.using(label=L_('Show comment sections'), optional=True)
    disabled = Boolean.using(label=L_('Disable this account forever'), optional=True)
    submit = String.using(default=L_('Save'), optional=True)


@frontend.route('/+usersettings', defaults=dict(part='main'), methods=['GET'])
@frontend.route('/+usersettings/<part>', methods=['GET', 'POST'])
def usersettings(part):
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'User Settings' # XXX

    # these forms can't be global because we need app object, which is only available within a request:
    class UserSettingsPersonalForm(Form):
        name = 'usersettings_personal' # "name" is duplicate
        name = String.using(label=L_('Name')).with_properties(placeholder=L_("The login name you want to use")).validated_by(Present())
        aliasname = String.using(label=L_('Alias-Name'), optional=True).with_properties(placeholder=L_("Your alias name (informational)"))
        openid = String.using(label=L_('OpenID'), optional=True).with_properties(placeholder=L_("Your OpenID address")).validated_by(URLValidator())
        #timezones_keys = sorted(Locale('en').time_zones.keys())
        timezones_keys = [unicode(tz) for tz in pytz.common_timezones]
        timezone = Enum.using(label=L_('Timezone')).valued(*timezones_keys)
        supported_locales = [Locale('en')] + app.babel_instance.list_translations()
        locales_available = sorted([(unicode(l), l.display_name) for l in supported_locales],
                                   key=lambda x: x[1])
        locales_keys = [l[0] for l in locales_available]
        locale = Enum.using(label=L_('Locale')).with_properties(labels=dict(locales_available)).valued(*locales_keys)
        submit = String.using(default=L_('Save'), optional=True)

    class UserSettingsUIForm(Form):
        name = 'usersettings_ui'
        themes_available = sorted([(unicode(t.identifier), t.name) for t in get_themes_list()],
                                  key=lambda x: x[1])
        themes_keys = [t[0] for t in themes_available]
        theme_name = Enum.using(label=L_('Theme name')).with_properties(labels=dict(themes_available)).valued(*themes_keys)
        css_url = String.using(label=L_('User CSS URL'), optional=True).with_properties(placeholder=L_("Give the URL of your custom CSS (optional)")).validated_by(URLValidator())
        edit_rows = Integer.using(label=L_('Editor size')).with_properties(placeholder=L_("Editor textarea height (0=auto)")).validated_by(Converted())
        results_per_page = Integer.using(label=L_('History results per page')).with_properties(placeholder=L_("Number of results per page (0=no paging)")).validated_by(ValueAtLeast(0))
        submit = String.using(default=L_('Save'), optional=True)

    dispatch = dict(
        personal=UserSettingsPersonalForm,
        password=UserSettingsPasswordForm,
        notification=UserSettingsNotificationForm,
        ui=UserSettingsUIForm,
        navigation=UserSettingsNavigationForm,
        options=UserSettingsOptionsForm,
    )
    FormClass = dispatch.get(part)
    if FormClass is None:
        # 'main' part or some invalid part
        return render_template('usersettings.html',
                               part='main',
                               item_name=item_name,
                              )
    if request.method == 'GET':
        form = FormClass.from_object(flaskg.user)
        form['submit'].set_default() # XXX from_object() kills all values
    elif request.method == 'POST':
        form = FormClass.from_flat(request.form)
        if form.validate():
            # successfully modified everything
            success = True
            if part == 'password':
                flaskg.user.enc_password = crypto.crypt_password(form['password1'].value)
                flaskg.user.save()
                flash(_("Your password has been changed."), "info")
            else:
                if part == 'personal':
                    if form['openid'].value != flaskg.user.openid and user.search_users(openid=form['openid'].value):
                        # duplicate openid
                        flash(_("This openid is already in use."), "error")
                        success = False
                    if form['name'].value != flaskg.user.name and user.search_users(name_exact=form['name'].value):
                        # duplicate name
                        flash(_("This username is already in use."), "error")
                        success = False
                if part == 'notification':
                    if (form['email'].value != flaskg.user.email and
                        user.search_users(email=form['email'].value) and app.cfg.user_email_unique):
                        # duplicate email
                        flash(_('This email is already in use'), 'error')
                        success = False
                if success:
                    form.update_object(flaskg.user, omit=['submit']) # don't save submit button value :)
                    flaskg.user.save()
                    return redirect(url_for('.usersettings'))
                else:
                    # reset to valid values
                    form = FormClass.from_object(flaskg.user)
                    form['submit'].set_default() # XXX from_object() kills all values
    return render_template('usersettings.html',
                           item_name=item_name,
                           part=part,
                           form=form,
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

        if tm is None:
            flaskg.user.delBookmark()
        else:
            flaskg.user.setBookmark(tm)
    else:
        flash(_("You must log in to use bookmarks."), "error")
    return redirect(url_for('.global_history'))


@frontend.route('/+diffraw/<path:item_name>')
def diffraw(item_name):
    # TODO get_item and get_revision calls may raise an AccessDeniedError.
    #      If this happens for get_item, don't show the diff at all
    #      If it happens for get_revision, we may just want to skip that rev in the list
    try:
        item = flaskg.storage.get_item(item_name)
    except AccessDeniedError:
        abort(403)
    rev1 = request.values.get('rev1')
    rev2 = request.values.get('rev2')
    return _diff_raw(item, rev1, rev2)


@frontend.route('/+diff/<path:item_name>')
def diff(item_name):
    item = flaskg.storage[item_name]
    bookmark_time = request.values.get('bookmark')
    if bookmark_time is not None:
        # this is how we get called from "recent changes"
        # try to find the latest rev1 before bookmark <date>
        revs = sorted([(rev.meta[MTIME], rev.revid) for rev in item.iter_revs()], reverse=True)
        for mtime, revid in revs:
            if mtime <= bookmark_time:
                rev1 = revid
                break
        else:
            rev1 = revid  # if we didn't find a rev, we just take oldest rev we have
        rev2 = CURRENT  # and compare it with latest we have
    else:
        # otherwise we should get the 2 revids directly
        rev1 = request.values.get('rev1')
        rev2 = request.values.get('rev2')
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


def _diff(item, revid1, revid2):
    oldrev = item[revid1]
    newrev = item[revid2]
    commonmt = _common_type(oldrev.meta[CONTENTTYPE], newrev.meta[CONTENTTYPE])

    try:
        item = Item.create(item.name, contenttype=commonmt, rev_id=newrev.revid)
    except AccessDeniedError:
        abort(403)
    rev_ids = [CURRENT]  # XXX TODO we need a reverse sorted list
    return render_template(item.diff_template,
                           item=item, item_name=item.name,
                           rev=item.rev,
                           first_rev_id=rev_ids[0],
                           last_rev_id=rev_ids[-1],
                           oldrev=oldrev,
                           newrev=newrev,
                          )


def _diff_raw(item, revid1, revid2):
    oldrev = item[revid1]
    newrev = item[revid2]
    commonmt = _common_type(oldrev, newrev)

    try:
        item = Item.create(item.name, contenttype=commonmt, rev_id=newrev.revid)
    except AccessDeniedError:
        abort(403)
    return item._render_data_diff_raw(oldrev, newrev)


@frontend.route('/+similar_names/<itemname:item_name>')
def similar_names(item_name):
    """
    list similar item names
    """
    start, end, matches = findMatches(item_name)
    keys = sorted(matches.keys())
    # TODO later we could add titles for the misc ranks:
    # 8 item_name
    # 4 "%s/..." % item_name
    # 3 "%s...%s" % (start, end)
    # 1 "%s..." % (start, )
    # 2 "...%s" % (end, )
    item_names = []
    for wanted_rank in [8, 4, 3, 1, 2, ]:
        for name in keys:
            rank = matches[name]
            if rank == wanted_rank:
                item_names.append(name)
    return render_template("item_link_list.html",
                           headline=_("Items with similar names"),
                           item_name=item_name, # XXX no item
                           item_names=item_names)


def findMatches(item_name, s_re=None, e_re=None):
    """ Find similar item names.

    :param item_name: name to match
    :param s_re: start re for wiki matching
    :param e_re: end re for wiki matching
    :rtype: tuple
    :returns: start word, end word, matches dict
    """
    item_names = [rev.meta[NAME] for rev in flaskg.storage.documents(all_revs=False, wikiname=app.cfg.interwikiname)]
    if item_name in item_names:
        item_names.remove(item_name)
    # Get matches using wiki way, start and end of word
    start, end, matches = wikiMatches(item_name, item_names, start_re=s_re, end_re=e_re)
    # Get the best 10 close matches
    close_matches = {}
    found = 0
    for name in closeMatches(item_name, item_names):
        if name not in matches:
            # Skip names already in matches
            close_matches[name] = 8
            found += 1
            # Stop after 10 matches
            if found == 10:
                break
    # Finally, merge both dicts
    matches.update(close_matches)
    return start, end, matches


def wikiMatches(item_name, item_names, start_re=None, end_re=None):
    """
    Get item names that starts or ends with same word as this item name.

    Matches are ranked like this:
        4 - item is subitem of item_name
        3 - match both start and end
        2 - match end
        1 - match start

    :param item_name: item name to match
    :param item_names: list of item names
    :param start_re: start word re (compile regex)
    :param end_re: end word re (compile regex)
    :rtype: tuple
    :returns: start, end, matches dict
    """
    if start_re is None:
        start_re = re.compile('([%s][%s]+)' % (config.chars_upper,
                                               config.chars_lower))
    if end_re is None:
        end_re = re.compile('([%s][%s]+)$' % (config.chars_upper,
                                              config.chars_lower))

    # If we don't get results with wiki words matching, fall back to
    # simple first word and last word, using spaces.
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
    for name in item_names:
        if name.startswith(subitem):
            matches[name] = 4
        else:
            if name.startswith(start):
                matches[name] = 1
            if name.endswith(end):
                matches[name] = matches.get(name, 0) + 2

    return start, end, matches


def closeMatches(item_name, item_names):
    """ Get close matches.

    Return all matching item names with rank above cutoff value.

    :param item_name: item name to match
    :param item_names: list of item names
    :rtype: list
    :returns: list of matching item names, sorted by rank
    """
    # Match using case insensitive matching
    # Make mapping from lower item names to item names.
    lower = {}
    for name in item_names:
        key = name.lower()
        if key in lower:
            lower[key].append(name)
        else:
            lower[key] = [name]

    # Get all close matches
    all_matches = difflib.get_close_matches(item_name.lower(), lower.keys(),
                                            len(lower), cutoff=0.6)

    # Replace lower names with original names
    matches = []
    for name in all_matches:
        matches.extend(lower[name])

    return matches


@frontend.route('/+sitemap/<item_name>')
def sitemap(item_name):
    """
    sitemap view shows item link structure, relative to current item
    """
    sitemap = NestedItemListBuilder().recurse_build([item_name])
    del sitemap[0] # don't show current item name as sole toplevel list item
    return render_template('sitemap.html',
                           item_name=item_name, # XXX no item
                           sitemap=sitemap,
                          )


class NestedItemListBuilder(object):
    def __init__(self):
        self.children = set()
        self.numnodes = 0
        self.maxnodes = 35 # approx. max count of nodes, not strict

    def recurse_build(self, names):
        result = []
        if self.numnodes < self.maxnodes:
            for name in names:
                self.children.add(name)
                result.append(name)
                self.numnodes += 1
                childs = self.childs(name)
                if childs:
                    childs = self.recurse_build(childs)
                    result.append(childs)
        return result

    def childs(self, name):
        # does not recurse
        try:
            item = flaskg.storage[name]
        except AccessDeniedError:
            return []
        rev = item[CURRENT]
        itemlinks = rev.meta.get(ITEMLINKS, [])
        return [child for child in itemlinks if self.is_ok(child)]

    def is_ok(self, child):
        if child not in self.children:
            if not flaskg.user.may.read(child):
                return False
            if flaskg.storage.has_item(child):
                self.children.add(child)
                return True
        return False


@frontend.route('/+tags')
def global_tags():
    """
    show a list or tag cloud of all tags in this wiki
    """
    item_name = request.values.get('item_name', '') # actions menu puts it into qs
    revs = flaskg.storage.documents(all_revs=False, wikiname=app.cfg.interwikiname)
    tags_counts = {}
    for rev in revs:
        tags = rev.meta.get(TAGS, [])
        logging.debug("name %s rev %s tags %s" % (rev.meta[NAME], rev.meta[REVID], tags))
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
            return "weight%d" % int(weight)  # weight0, ..., weight9
        tags = [(cls(count), tag) for tag, count in tags_counts]
    else:
        tags = []
    return render_template("global_tags.html",
                           headline=_("All tags in this wiki"),
                           item_name=item_name,
                           tags=tags)


@frontend.route('/+tags/<itemname:tag>')
def tagged_items(tag):
    """
    show all items' names that have tag <tag>
    """
    query = And([Term(WIKINAME, app.cfg.interwikiname), Term(TAGS, tag), ])
    revs = flaskg.storage.search(query, all_revs=False, sortedby=NAME_EXACT, limit=None)
    item_names = [rev.meta[NAME] for rev in revs]
    return render_template("item_link_list.html",
                           headline=_("Items tagged with %(tag)s", tag=tag),
                           item_name=tag,
                           item_names=item_names)

