# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Ticket itemtype

TODO: Tickets require more work. Key requirements include but are not limited to:

 - ability to edit the original description or subsequent comments to correct typos
 - rework global history and global index to show or not show tickets and/or comments
 - rework page trail, subscriptions, navigation links to show something other than rev ids or timestamps
 - some method to override the default parser (text/x.moin.wiki) for a new ticket or comment
 - add more comments to the code

A ticket is a unique itemtype, the initial ticket consists of a description and meta data.
Some of the meta data fields are unique to tickets.

The original design called for tickets to be nameless. Instead of a name, tickets would
have a summary in meta data that would be too long for a typical wiki item name. However,
it is not currently possible to create a nameless item, so as a workaround, tickets are created
with a name similar to: ticket_2016_09_21-09_19_29.

When a ticket's meta data is updated, a new revision is created and the ticket's name is removed.
After the first update, the current revision has an Old Name, after the second meta data update,
the current name and Old Name are both displayed as None.

Ticket comments and ticket comments to comments are presently created without an item type.
This is an issue because when a wiki is dumped and restored, all comments are tagged with an
itemtype of "default". This is probably not wanted, but no other problems after a restore were
noted.

As a workaround to the issue of creating nameless items, comments are created with a
name similar to: comment_2016_09_21-09_19_29. As comments can not currently be updated,
the name is never removed. Comments and comments to comments are linked to the original
ticket through a refers_to field preserved in meta data.
"""

import time
import datetime

from flask import request, abort, redirect, url_for
from flask import g as flaskg
from flask import current_app as app

from markupsafe import Markup

from whoosh.query import Term, And

from moin.i18n import L_
from moin.themes import render_template
from moin.forms import (
    Form,
    OptionalMultilineText,
    SmallNatural,
    Tags,
    Reference,
    BackReference,
    SelectSubmit,
    Text,
    Search,
    File,
)
from moin.storage.middleware.protecting import AccessDenied
from moin.constants.keys import (
    ITEMTYPE,
    CONTENTTYPE,
    ITEMID,
    CURRENT,
    SUPERSEDED_BY,
    SUBSCRIPTIONS,
    DEPENDS_ON,
    MTIME,
    TAGS,
    NAME,
    SUMMARY,
    ELEMENT,
    NAMESPACE,
    WIKINAME,
    REFERS_TO,
    CONTENT,
    ACTION_TRASH,
)
from moin.constants.contenttypes import CONTENTTYPE_USER
from moin.constants.itemtypes import ITEMTYPE_TICKET
from moin.items import Item, Contentful, register, BaseModifyForm, get_itemtype_specific_tags, IndexEntry
from moin.items.content import NonExistentContent
from moin.utils.interwiki import CompositeName
from moin.constants.forms import WIDGET_SEARCH

USER_QUERY = Term(CONTENTTYPE, CONTENTTYPE_USER)
TICKET_QUERY = Term(ITEMTYPE, ITEMTYPE_TICKET)

Rating = SmallNatural.using(optional=True).with_properties(lower=1, upper=5)


def get_itemid_short_summary(rev):
    return f"{rev.meta[ITEMID][:4]} ({rev.meta[SUMMARY][:50]})"


def get_name(rev):
    return rev.meta[NAME][0]


OptionalTicketReference = (
    Reference.to(TICKET_QUERY).using(optional=True).with_properties(label_getter=get_itemid_short_summary)
)
OptionalUserReference = (
    Reference.to(USER_QUERY).using(optional=True).with_properties(empty_label="(Nobody)", label_getter=get_name)
)


class AdvancedSearchForm(Form):
    q = Search
    summary = Text.using(label=L_("Summary"), optional=False).with_properties(
        widget=WIDGET_SEARCH, placeholder=L_("Find Tickets")
    )
    effort = Rating.using(label=L_("Effort"))
    difficulty = Rating.using(label=L_("Difficulty"))
    severity = Rating.using(label=L_("Severity"))
    priority = Rating.using(label=L_("Priority"))
    tags = Tags.using(optional=True)
    assigned_to = OptionalUserReference.using(label=L_("Assigned To"))
    author = OptionalUserReference.using(label=L_("Author"))


class TicketMetaForm(Form):
    summary = Text.using(label=L_("Summary"), optional=False).with_properties(
        widget=WIDGET_SEARCH, placeholder=L_("One-line summary")
    )
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
        self["supersedes"].set(Term(SUPERSEDED_BY, id_))
        self["required_by"].set(Term(DEPENDS_ON, id_))
        self["subscribers"].set(Term(SUBSCRIPTIONS, id_))


class TicketForm(BaseModifyForm):
    meta = TicketMetaForm
    backrefs = TicketBackRefForm
    message = OptionalMultilineText.using(label=L_("Message")).with_properties(rows=8, cols=80)
    data_file = File.using(optional=True, label=L_("Replace content with uploaded file:"))

    def _load(self, item):
        meta = item.prepare_meta_for_modify(item.meta)
        self["meta"].set(meta, "duck")
        # XXX need a more explicit way to test for item creation/modification
        if ITEMID in item.meta:
            self["backrefs"]._load(item)


class TicketSubmitForm(TicketForm):
    submit_label = L_("Submit ticket")

    def _dump(self, item):
        # initial metadata for Ticket-itemtyped item
        meta = {
            ITEMTYPE: item.itemtype,
            # XXX support other markups
            CONTENTTYPE: "text/x.moin.wiki;charset=utf-8",
            "closed": False,
        }
        meta.update(self["meta"].value)
        return meta, message_markup(self["message"].value), None, self["data_file"].value


class TicketUpdateForm(TicketForm):
    submit = SelectSubmit.valued("update", "update_negate_status")

    def _load(self, item):
        super()._load(item)
        self["submit"].properties["labels"] = {
            "update": L_("Update ticket"),
            "update_negate_status": (
                L_("Update & reopen ticket") if item.meta.get("closed") else L_("Update & close ticket")
            ),
        }

    def _dump(self, item):
        # Since the metadata form for tickets is an incomplete one, we load the
        # original meta and update it with those from the metadata editor
        meta = item.meta_filter(item.prepare_meta_for_modify(item.meta))

        # create an "Update" comment if metadata changes
        meta_changes = []
        for key, value in self["meta"].value.items():
            if not meta.get(key) == value:
                if key == TAGS:
                    original = ", ".join(meta.get(key))
                    new = ", ".join(value)
                elif key == DEPENDS_ON or key == SUPERSEDED_BY:
                    original = meta.get(key)[:4]
                    new = value[:4]
                else:
                    original = meta.get(key)
                    new = value
                msg = L_("{key} changed from {original} to {new}").format(key=key, original=original, new=new)
                meta_changes.append(" * " + msg)
        if meta_changes:
            meta_changes = "Meta updates:\n" + "\n".join(meta_changes)
            create_comment(meta, meta_changes)
        meta.update(self["meta"].value)

        if self["submit"].value == "update_negate_status":
            meta["closed"] = not meta.get("closed")

        data = item.content.data_storage_to_internal(item.content.data)
        message = self["message"].value

        if meta_changes:
            # user changed meta, create new revision of ticket
            item.modify(meta, data)

        return meta, data, message, self["data_file"].value


def message_markup(message):
    """
    Add a heading with author and timestamp to message (aka ticket description).
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    heading = L_("{author} wrote on {timestamp}:").format(author=flaskg.user.name[0], timestamp=timestamp)
    message = f"{heading}\n\n{message}"
    return """{{{{{{#!wiki moin-ticket
%(message)s
}}}}}}""" % dict(
        message=message
    )


def check_itemid(self):
    # once a ticket has both name and itemid, use itemid
    if self.meta.get(ITEMID) and self.meta.get(NAME):
        query = And([Term(WIKINAME, app.cfg.interwikiname), Term(REFERS_TO, self.meta[NAME])])
        revs = flaskg.storage.search(query, limit=None)
        prefix = self.meta[NAME][0] + "/"
        for rev in revs:  # TODO: if this is not dead code add a comment how to get here
            old_names = rev.meta[NAME]
            for old_name in old_names:
                file_name = old_name[len(prefix) :]
                try:
                    new_name = self.meta[ITEMID] + "/" + file_name
                    item = Item.create(new_name)
                    item.modify({}, rev.meta[CONTENT], refers_to=self.meta[ITEMID], element="file")
                    item = Item.create(old_name)
                    item._save(item.meta, name=old_name, action=ACTION_TRASH)  # delete
                except AccessDenied:
                    abort(403)


def file_upload(self, data_file):
    contenttype = data_file.content_type  # guess by browser, based on file name
    data = data_file.stream
    check_itemid(self)
    if self.meta.get(ITEMID) and self.meta.get(NAME):
        item_name = self.meta[ITEMID] + "/" + data_file.filename
        refers_to = self.meta[ITEMID]
    else:
        item_name = self.fqname.value + "/" + data_file.filename
        refers_to = self.fqname.value
    try:
        item = Item.create(item_name)
        item.modify({}, data, contenttype_guessed=contenttype, refers_to=refers_to, element="file")
    except AccessDenied:
        abort(403)


def get_files(self):
    check_itemid(self)
    if self.meta.get(ITEMID) and self.meta.get(NAME):
        refers_to = self.meta[ITEMID]
        prefix = self.meta[ITEMID] + "/"
    else:
        refers_to = self.fqname.value
        prefix = self.fqname.value + "/"
    query = And([Term(WIKINAME, app.cfg.interwikiname), Term(REFERS_TO, refers_to), Term(ELEMENT, "file")])
    revs = flaskg.storage.search(query, limit=None)
    files = []
    for rev in revs:
        names = rev.meta[NAME]
        for name in names:
            relname = name[len(prefix) :]
            file_fqname = CompositeName(rev.meta[NAMESPACE], ITEMID, rev.meta[ITEMID])
            files.append(IndexEntry(relname, file_fqname, rev.meta))
    return files


def get_comments(self):
    """
    Return a list of roots (comments to original ticket) and a dict of comments (comments to comments).
    """
    refers_to = self.meta[ITEMID]
    query = And([Term(WIKINAME, app.cfg.interwikiname), Term(REFERS_TO, refers_to), Term(ELEMENT, "comment")])
    revs = flaskg.storage.search(query, sortedby=[MTIME], limit=None)
    comments = dict()  # {rev: [],...} comments to a comment
    lookup = dict()  # {itemid: rev,...}
    roots = []
    revs = list(revs)
    for rev in revs:
        lookup[rev.meta[ITEMID]] = rev
        comments[rev] = []
    for rev in revs:
        if not rev.meta["reply_to"]:
            roots.append(rev)
        else:
            parent = lookup[rev.meta["reply_to"]]
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
            # recursion is used to place comments in order based on comment hierarchy and date
            build_tree(comments, comment, comment_tree, indent + 20)
        return comment_tree
    else:
        return []


def create_comment(meta, message):
    """
    Create a new item comment against original description, refers_to links to original.
    """
    current_timestamp = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    item_name = meta[ITEMID] + "/" + "comment_" + str(current_timestamp)
    item = Item.create(item_name)
    item.modify(
        {},
        data=message,
        element="comment",
        contenttype_guessed="text/x.moin.wiki;charset=utf-8",
        refers_to=meta[ITEMID],
        reply_to="",
        author=flaskg.user.name[0],
        timestamp=time.ctime(),
    )


@register
class Ticket(Contentful):
    itemtype = ITEMTYPE_TICKET
    display_name = L_("Ticket")
    description = L_("Ticket item")
    submit_template = "ticket/submit.html"
    modify_template = "ticket/modify.html"

    def do_show(self, revid, **kwargs):
        if revid != CURRENT:
            # TODO When requesting a historical version, show a readonly view
            abort(403)
        else:
            return self.do_modify()

    def do_modify(self):
        """
        Process new ticket, changes to ticket meta data, and/or a new comment against original ticket description.

        User has clicked "Submit ticket" or "Update ticket" button to get here. If user clicks Save button to
        add a comment to a prior comment it is not processed here - see /+comment in views.py.
        """
        is_new = isinstance(self.content, NonExistentContent)
        closed = self.meta.get("closed")

        Form = TicketSubmitForm if is_new else TicketUpdateForm

        if request.method in ["GET", "HEAD"]:
            form = Form.from_item(self)
        elif request.method == "POST":
            form = Form.from_request(request)
            if form.validate():
                # save new ticket revision if ticket meta has changed
                meta, data, message, data_file = form._dump(self)
                try:
                    if not is_new and message:
                        # user created a new comment
                        create_comment(self.meta, message)
                    if is_new:
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
                    return redirect(url_for(".show_item", item_name=fqname))
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
            ordered_comments += [(root, 0)] + build_tree(comments, root, [], 0)
        return render_template(
            self.submit_template if is_new else self.modify_template,
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
