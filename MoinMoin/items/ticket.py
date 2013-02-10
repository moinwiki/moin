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
from MoinMoin.forms import Form, OptionalText, OptionalMultilineText, Submit, SmallNatural, Tags, Reference, BackReference
from MoinMoin.storage.middleware.protecting import AccessDenied
from MoinMoin.constants.keys import ITEMTYPE, CONTENTTYPE, ITEMID, CURRENT
from MoinMoin.constants.contenttypes import CONTENTTYPE_USER
from MoinMoin.items import Item, Contentful, register, BaseModifyForm
from MoinMoin.items.content import NonExistentContent


ITEMTYPE_TICKET = u'ticket'

USER_QUERY = Term(CONTENTTYPE, CONTENTTYPE_USER)
TICKET_QUERY = Term(ITEMTYPE, ITEMTYPE_TICKET)

Rating = SmallNatural.using(optional=True).with_properties(lower=1, upper=5)
OptionalTicketReference = Reference.to(TICKET_QUERY).using(optional=True)
OptionalUserReference = Reference.to(USER_QUERY).using(optional=True).with_properties(empty_label='(Nobody)')

class TicketMetaForm(Form):
    summary = OptionalText.using(label=L_("Summary")).with_properties(placeholder=L_("One-line summary of the item"))
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
        self['supersedes'].set(Term('superseded_by', id_))
        self['required_by'].set(Term('depends_on', id_))
        self['subscribers'].set(Term('subscribed_items', id_))

class TicketForm(BaseModifyForm):
    meta = TicketMetaForm
    backrefs = TicketBackRefForm
    message = OptionalMultilineText.using(label=L_("Message")).with_properties(rows=8, cols=80)
    submit = Submit.using(default=L_("Update ticket"))

    def _load(self, item):
        meta = item.prepare_meta_for_modify(item.meta)
        self['meta'].set(meta, 'duck')
        # XXX need a more explicit way to test for item creation/modification
        if ITEMID in item.meta:
            self['backrefs']._load(item)


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
''' % dict(author=flaskg.user.name, timestamp=time.time(), message=message)


@register
class Ticket(Contentful):
    itemtype = ITEMTYPE_TICKET
    display_name = L_('Ticket')
    description = L_('Ticket item')
    modify_template = 'ticket.html'

    def do_show(self, revid):
        if revid != CURRENT:
            # TODO When requesting a historical version, show a readonly view
            abort(403)
        else:
            return self.do_modify()

    def do_modify(self):
        if request.method in ['GET', 'HEAD']:
            form = TicketForm.from_item(self)
        elif request.method == 'POST':
            form = TicketForm.from_request(request)
            if form.validate():
                meta = form['meta'].value
                meta.update({
                    ITEMTYPE: self.itemtype,
                    # XXX support other markups
                    CONTENTTYPE: 'text/x.moin.wiki;charset=utf-8',
                })

                if isinstance(self.content, NonExistentContent):
                    data = u''
                else:
                    data = self.content.data_storage_to_internal(self.content.data)
                message = form['message'].value
                if message:
                    data += message_markup(message)

                try:
                    self.modify(meta, data)
                except AccessDenied:
                    abort(403)
                else:
                    return redirect(url_for('.show_item', item_name=self.name))
        if isinstance(self.content, NonExistentContent):
            is_new = True
            # XXX suppress the "foo doesn't exist. Create it?" dummy content
            data_rendered = None
            form['submit'] = L_('Submit ticket')
        else:
            is_new = False
            data_rendered = Markup(self.content._render_data())

        return render_template(self.modify_template,
                               is_new=is_new,
                               item_name=self.name,
                               data_rendered=data_rendered,
                               form=form,
                              )
