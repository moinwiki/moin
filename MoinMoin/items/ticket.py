# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Ticket itemtype
"""


from __future__ import absolute_import, division

import time
import datetime

from flask import request, abort, redirect, url_for
from flask import g as flaskg
from flask import current_app as app

from jinja2 import Markup

from whoosh.query import Term, And

from MoinMoin.i18n import L_
from MoinMoin.themes import render_template
from MoinMoin.forms import (Form, OptionalText, OptionalMultilineText, SmallNatural, Tags,
                            Reference, BackReference, SelectSubmit, Text, Search, File)
from MoinMoin.storage.middleware.protecting import AccessDenied
from MoinMoin.constants.keys import (ITEMTYPE, CONTENTTYPE, ITEMID, CURRENT,
                                     SUPERSEDED_BY, SUBSCRIPTIONS, DEPENDS_ON, MTIME, TAGS,
                                     NAME, SUMMARY, ELEMENT, NAMESPACE, WIKINAME, REFERS_TO, CONTENT, ACTION_TRASH)
from MoinMoin.constants.contenttypes import CONTENTTYPE_USER
from MoinMoin.items import Item, Contentful, register, BaseModifyForm, get_itemtype_specific_tags, IndexEntry
from MoinMoin.items.content import NonExistentContent
from MoinMoin.util.interwiki import CompositeName
from MoinMoin.constants.forms import *
ITEMTYPE_TICKET = u'ticket'

USER_QUERY = Term(CONTENTTYPE, CONTENTTYPE_USER)
TICKET_QUERY = Term(ITEMTYPE, ITEMTYPE_TICKET)

Rating = SmallNatural.using(optional=True).with_properties(lower=1, upper=5)


def get_itemid_short_summary(rev):
    return '{itemid} ({summary})'.format(itemid=rev.meta[ITEMID][:4], summary=rev.meta[SUMMARY][:50])


def get_name(rev):
    return rev.meta[NAME][0]


OptionalTicketReference = Reference.to(
    TICKET_QUERY,
).using(
    optional=True,
).with_properties(
    label_getter=get_itemid_short_summary,
)
OptionalUserReference = Reference.to(
    USER_QUERY,
).using(
    optional=True,
).with_properties(
    empty_label='(Nobody)',
    label_getter=get_name,
)


class AdvancedSearchForm(Form):
    q = Search
    summary = Text.using(label=L_("Summary"), optional=False).with_properties(widget=WIDGET_SEARCH, placeholder=L_("Find Tickets"))
    effort = Rating.using(label=L_("Effort"))
    difficulty = Rating.using(label=L_("Difficulty"))
    severity = Rating.using(label=L_("Severity"))
    priority = Rating.using(label=L_("Priority"))
    tags = Tags.using(optional=True)
    assigned_to = OptionalUserReference.using(label=L_("Assigned To"))
    author = OptionalUserReference.using(label=L_("Author"))


class TicketMetaForm(Form):
    summary = Text.using(label=L_("Summary"), optional=False).with_properties(widget=WIDGET_SEARCH, placeholder=L_("One-line summary"))
    effort = Rating.using(label=L_("Effort"))
    difficulty = Rating.using(label=L_("Difficulty"))
    severity = Rating.using(label=L_("Severity"))
    priority = Rating.using(label=L_("Priority"))
    tags = Tags.using(optional=True)
    assigned_to = OptionalUserReference.using(label=L_("Assigned To"))
    superseded_by = OptionalTicketReference.using(label=L_("Superseded By"))
    depends_on = OptionalTicketReference.using(label=L_("Depends On"))


class TicketBackRefForm(Form):
    supersedes = BackReference.using(label=L_("Supersedes"))
    required_by = BackReference.using(label=L_("Required By"))
    subscribers = BackReference.using(label=L_("Subscribers"))

    def _load(self, item):
        id_ = item.meta[ITEMID]
        self['supersedes'].set(Term(SUPERSEDED_BY, id_))
        self['required_by'].set(Term(DEPENDS_ON, id_))
        self['subscribers'].set(Term(SUBSCRIPTIONS, id_))


class TicketForm(BaseModifyForm):
    meta = TicketMetaForm
    backrefs = TicketBackRefForm
    message = OptionalMultilineText.using(label=L_("Message")).with_properties(rows=8, cols=80)
    data_file = File.using(optional=True, label=L_('Upload file:'))

    def _load(self, item):
        meta = item.prepare_meta_for_modify(item.meta)
        self['meta'].set(meta, 'duck')
        # XXX need a more explicit way to test for item creation/modification
        if ITEMID in item.meta:
            self['backrefs']._load(item)


class TicketSubmitForm(TicketForm):
    submit_label = L_("Submit ticket")

    def _dump(self, item):
        # initial metadata for Ticket-itemtyped item
        meta = {
            ITEMTYPE: item.itemtype,
            # XXX support other markups
            CONTENTTYPE: 'text/x.moin.wiki;charset=utf-8',
            'closed': False,
        }
        meta.update(self['meta'].value)
        return meta, message_markup(self['message'].value), None, self['data_file'].value


class TicketUpdateForm(TicketForm):
    submit = SelectSubmit.valued('update', 'update_negate_status')

    def _load(self, item):
        super(TicketUpdateForm, self)._load(item)
        self['submit'].properties['labels'] = {
            'update': L_('Update ticket'),
            'update_negate_status': (L_('Update & reopen ticket') if item.meta.get('closed')
                                     else L_('Update & close ticket'))
        }

    def _dump(self, item):
        # Since the metadata form for tickets is an incomplete one, we load the
        # original meta and update it with those from the metadata editor
        meta = item.meta_filter(item.prepare_meta_for_modify(item.meta))

        # create an "Update" comment if metadata changes
        meta_changes = []
        for key, value in self['meta'].value.iteritems():
            if not meta.get(key) == value:
                if key == TAGS:
                    original = ', '.join(meta.get(key))
                    new = ', '.join(value)
                elif key == DEPENDS_ON or key == SUPERSEDED_BY:
                    original = meta.get(key)[:4]
                    new = value[:4]
                else:
                    original = meta.get(key)
                    new = value
                msg = L_('{key} changed from {original} to {new}'.format(key=key, original=original, new=new))
                meta_changes.append(u' * ' + msg)
        if meta_changes:
            meta_changes = 'Meta updates:\n' + '\n'.join(meta_changes)
            create_comment(meta, meta_changes)
        meta.update(self['meta'].value)

        if self['submit'].value == 'update_negate_status':
            meta['closed'] = not meta.get('closed')

        data = item.content.data_storage_to_internal(item.content.data)
        message = self['message'].value

        return meta, data, message, self['data_file'].value


# XXX Ideally we should generate DOM instead of moin wiki source. But
# currently this is not very useful, since
# * DOM cannot be stored directly, it has to be converted to some markup first
# * DOM -> markup conversion is only available for moinwiki

# XXX How to do i18n on this?

def message_markup(message):
    return u'''{{{{{{#!wiki moin-ticket
%(author)s wrote on <<DateTime(%(timestamp)d)>>:

%(message)s
}}}}}}
''' % dict(author=flaskg.user.name[0], timestamp=time.time(), message=message)


def check_itemid(self):
    # once a ticket has both name and itemid, use itemid
    if self.meta.get(ITEMID) and self.meta.get(NAME):
        query = And([Term(WIKINAME, app.cfg.interwikiname), Term(REFERS_TO, self.meta[NAME])])
        revs = flaskg.storage.search(query, limit=None)
        prefix = self.meta[NAME][0] + '/'
        for rev in revs:  # TODO: if this is not dead code add a comment how to get here
            old_names = rev.meta[NAME]
            for old_name in old_names:
                file_name = old_name[len(prefix):]
                try:
                    new_name = self.meta[ITEMID] + '/' + file_name
                    item = Item.create(new_name)
                    item.modify({}, rev.meta[CONTENT], refers_to=self.meta[ITEMID], element=u'file')
                    item = Item.create(old_name)
                    item._save(item.meta, name=old_name, action=ACTION_TRASH)  # delete
                except AccessDenied:
                    abort(403)


def file_upload(self, data_file):
    contenttype = data_file.content_type  # guess by browser, based on file name
    data = data_file.stream
    check_itemid(self)
    if self.meta.get(ITEMID) and self.meta.get(NAME):
        item_name = self.meta[ITEMID] + '/' + data_file.filename
        refers_to = self.meta[ITEMID]
    else:
        item_name = self.fqname.value + '/' + data_file.filename
        refers_to = self.fqname.value
    try:
        item = Item.create(item_name)
        item.modify({}, data, contenttype_guessed=contenttype, refers_to=refers_to, element=u'file')
    except AccessDenied:
        abort(403)


def get_files(self):
    check_itemid(self)
    if self.meta.get(ITEMID) and self.meta.get(NAME):
        refers_to = self.meta[ITEMID]
        prefix = self.meta[ITEMID] + '/'
    else:
        refers_to = self.fqname.value
        prefix = self.fqname.value + '/'
    query = And([Term(WIKINAME, app.cfg.interwikiname), Term(REFERS_TO, refers_to), Term(ELEMENT, u'file')])
    revs = flaskg.storage.search(query, limit=None)
    files = []
    for rev in revs:
        names = rev.meta[NAME]
        for name in names:
            relname = name[len(prefix):]
            file_fqname = CompositeName(rev.meta[NAMESPACE], ITEMID, rev.meta[ITEMID])
            files.append(IndexEntry(relname, file_fqname, rev.meta))
    return files


def get_comments(self):
    """
    Return a list of roots (comments to original ticket) and a dict of comments (comments to comments).
    """
    refers_to = self.meta[ITEMID]
    query = And([Term(WIKINAME, app.cfg.interwikiname), Term(REFERS_TO, refers_to), Term(ELEMENT, u'comment')])
    revs = flaskg.storage.search(query, sortedby=[MTIME], limit=None)
    comments = dict()  # {rev: [],...} comments to a comment
    lookup = dict()  # {itemid: rev,...}
    roots = []
    revs = list(revs)
    for rev in revs:
        lookup[rev.meta[ITEMID]] = rev
        comments[rev] = []
    for rev in revs:
        if not rev.meta['reply_to']:
            roots.append(rev)
        else:
            parent = lookup[rev.meta['reply_to']]
            comments[parent] = comments.get(parent, []) + [rev]
    return comments, roots


def render_comment_data(comment):
    """
    Return a rendered comment.
    """
    item = Item.create(name=comment.name)
    txt = item.content._render_data()
    return txt


def build_tree(comments, root, comment_tree, indent):
    """
    Return an ordered list of comments related to a root comment.

    :param comments: dict containing list of comments related to root
    :param root: a comment to the ticket description
    :param comment_tree: empty list on first call, may be populated through recursion
    :rtype: list of comments
    :returns: list of tuples [comments, indent]  pertaining to a comment against original description
    """
    if comments[root]:
        for comment in comments[root]:
            comment_tree.append((comment, indent + 20))  # where 20, 40,... will become an indented left margin
            # recursion is used to place comments in order based on comment heirarchy and date
            build_tree(comments, comment, comment_tree, indent + 20)
        return comment_tree
    else:
        return []


def create_comment(meta, message):
    """
    Create a new item comment against original description, refers_to links to original.
    """
    current_timestamp = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    item_name = meta[ITEMID] + u'/' + u'comment_' + unicode(current_timestamp)
    item = Item.create(item_name)
    item.modify({}, data=message, element=u'comment', contenttype_guessed=u'text/x.moin.wiki;charset=utf-8',
                refers_to=meta[ITEMID], reply_to=u'', author=flaskg.user.name[0], timestamp=time.ctime())


@register
class Ticket(Contentful):
    itemtype = ITEMTYPE_TICKET
    display_name = L_('Ticket')
    description = L_('Ticket item')
    submit_template = 'ticket/submit.html'
    modify_template = 'ticket/modify.html'

    def do_show(self, revid):
        if revid != CURRENT:
            # TODO When requesting a historical version, show a readonly view
            abort(403)
        else:
            return self.do_modify()

    def do_modify(self):
        """
        Process changes to meta data and/or a new comment against original ticket description.

        User has clicked "update ticket" button to get here. If user clicks Save button to
        add a comment to a prior comment it is not processed here - see /+comment in views.py.
        """
        is_new = isinstance(self.content, NonExistentContent)
        closed = self.meta.get('closed')

        Form = TicketSubmitForm if is_new else TicketUpdateForm

        if request.method in ['GET', 'HEAD']:
            form = Form.from_item(self)
        elif request.method == 'POST':
            form = Form.from_request(request)
            if form.validate():
                meta, data, message, data_file = form._dump(self)
                try:
                    if not is_new and message:
                        # user created a new comment
                        create_comment(self.meta, message)
                    # TODO: next line creates new revision of original ticket even if nothing has changed, deletes name, sets trash=True
                    self.modify(meta, data)
                    if data_file:
                        file_upload(self, data_file)
                except AccessDenied:
                    abort(403)
                else:
                    try:
                        fqname = CompositeName(self.meta[NAMESPACE], ITEMID, self.meta[ITEMID])
                    except KeyError:
                        fqname = self.fqname
                    return redirect(url_for('.show_item', item_name=fqname))
        if is_new:
            data_rendered = None
            files = {}
            roots = []
            comments = {}
        else:
            data_rendered = Markup(self.content._render_data())
            files = get_files(self)
            comments, roots = get_comments(self)
        suggested_tags = get_itemtype_specific_tags(ITEMTYPE_TICKET)
        ordered_comments = []  # list of tuples [(comment, indent),,, ]
        for root in roots:
            ordered_comments += [(root, 0), ] + build_tree(comments, root, [], 0)
        return render_template(self.submit_template if is_new else self.modify_template,
                               is_new=is_new,
                               closed=closed,
                               item_name=self.name,
                               data_rendered=data_rendered,
                               form=form,
                               suggested_tags=suggested_tags,
                               item=self,
                               files=files,
                               datetime=datetime.datetime,
                               ordered_comments=ordered_comments,
                               render_comment_data=render_comment_data,
                              )
