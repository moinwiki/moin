# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Ticket itemtype
"""


from __future__ import absolute_import, division

import time

from flask import request, abort, redirect, url_for
from flask import g as flaskg

from jinja2 import Markup

from whoosh.query import Term

from MoinMoin.i18n import L_
from MoinMoin.themes import render_template
from MoinMoin.forms import (Form, OptionalText, OptionalMultilineText, SmallNatural, Tags,
                            Reference, BackReference, SelectSubmit, Text)
from MoinMoin.storage.middleware.protecting import AccessDenied
from MoinMoin.constants.keys import (ITEMTYPE, CONTENTTYPE, ITEMID, CURRENT,
                                     SUPERSEDED_BY, SUBSCRIPTIONS, DEPENDS_ON, NAME, SUMMARY)
from MoinMoin.constants.contenttypes import CONTENTTYPE_USER
from MoinMoin.items import Item, Contentful, register, BaseModifyForm
from MoinMoin.items.content import NonExistentContent
from MoinMoin.constants.keys import LATEST_REVS, TAGS


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


class TicketMetaForm(Form):
    summary = Text.using(label=L_("Summary")).with_properties(placeholder=L_("One-line summary of the item"))
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
        return meta, message_markup(self['message'].value)


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
        meta.update(self['meta'].value)
        if self['submit'].value == 'update_negate_status':
            meta['closed'] = not meta.get('closed')

        data = item.content.data_storage_to_internal(item.content.data)
        message = self['message'].value
        if message:
            data += message_markup(message)

        return meta, data


# XXX Ideally we should generate DOM instead of moin wiki source. But
# currently this is not very useful, since
# * DOM cannot be stored directly, it has to be converted to some markup first
# * DOM -> markup conversion is only available for moinwiki

# XXX How to do i18n on this?

def message_markup(message):
    return u'''{{{{{{#!wiki tip
%(author)s wrote on <<DateTime(%(timestamp)d)>>:

%(message)s
}}}}}}
''' % dict(author=flaskg.user.name[0], timestamp=time.time(), message=message)


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
        is_new = isinstance(self.content, NonExistentContent)
        closed = self.meta.get('closed')

        Form = TicketSubmitForm if is_new else TicketUpdateForm

        if request.method in ['GET', 'HEAD']:
            form = Form.from_item(self)
        elif request.method == 'POST':
            form = Form.from_request(request)
            if form.validate():
                meta, data = form._dump(self)
                try:
                    self.modify(meta, data)
                except AccessDenied:
                    abort(403)
                else:
                    return redirect(url_for('.show_item', item_name=self.name))

        # XXX When creating new item, suppress the "foo doesn't exist. Create it?" dummy content
        data_rendered = None if is_new else Markup(self.content._render_data())
        with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
            suggested_tags = list(searcher.field_terms(TAGS))

            return render_template(self.submit_template if is_new else self.modify_template,
                                   is_new=is_new,
                                   closed=closed,
                                   item_name=self.name,
                                   data_rendered=data_rendered,
                                   form=form,
                                   suggested_tags=suggested_tags,
                                  )
