# Copyright: 2012 MoinMoin:PavelSviderski
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Blog itemtype
"""


from datetime import datetime

from flask import request, abort
from flask import g as flaskg
from flask import current_app as app

from whoosh.query import Term, And, Prefix
from whoosh.sorting import FunctionFacet

from moin.i18n import L_
from moin.themes import render_template
from moin.forms import Text, Tags, DateTime
from moin.storage.middleware.protecting import AccessDenied
from moin.constants.keys import NAME_EXACT, WIKINAME, ITEMTYPE, MTIME, PTIME, TAGS
from moin.items import Item, Default, register, BaseMetaForm
from moin.utils.interwiki import split_fqname


ITEMTYPE_BLOG = "blog"
ITEMTYPE_BLOG_ENTRY = "blogentry"


class BlogMetaForm(BaseMetaForm):
    supertags = Tags.using(label=L_("Supertags (Categories)")).with_properties(
        placeholder=L_("Ordered comma separated list of tags")
    )


class BlogEntryMetaForm(BaseMetaForm):
    summary = Text.using(label=L_("Title (required)", optional=False)).with_properties(
        placeholder=L_("One-line title of the blog entry")
    )
    ptime = DateTime.using(label=L_("Publication time (UTC)"), optional=True)


@register
class Blog(Default):
    itemtype = ITEMTYPE_BLOG
    display_name = L_("Blog")
    description = L_("Blog item")
    order = 0

    class _ModifyForm(Default._ModifyForm):
        meta_form = BlogMetaForm
        meta_template = "blog/modify_main_meta.html"

    def do_show(self, revid, **kwargs):
        """
        Show a blog item and a list of its blog entries below it.

        If tag GET-parameter is defined, the list of blog entries consists only
        of those entries that contain the tag value in their lists of tags.
        """
        # for now it is just one tag=value, later it could be tag=value1&tag=value2&...
        tag = request.values.get("tag")
        prefix = self.name + "/"
        terms = [
            Term(WIKINAME, app.cfg.interwikiname),
            # Only blog entry itemtypes
            Term(ITEMTYPE, ITEMTYPE_BLOG_ENTRY),
            # Only sub items of this item
            Prefix(NAME_EXACT, prefix),
        ]
        if tag:
            terms.append(Term(TAGS, tag))
        query = And(terms)

        def ptime_sort_key(searcher, docnum):
            """
            Compute the publication time key for blog entries sorting.

            If PTIME is not defined, we use MTIME.
            """
            fields = searcher.stored_fields(docnum)
            ptime = fields.get(PTIME, fields[MTIME])
            return ptime

        ptime_sort_facet = FunctionFacet(ptime_sort_key)

        revs = flaskg.storage.search(query, sortedby=ptime_sort_facet, reverse=True, limit=None)
        blog_entry_items = [Item.create(rev.name, rev_id=rev.revid) for rev in revs]
        return render_template(
            "blog/main.html",
            item_name=self.name,
            fqname=split_fqname(self.name),
            blog_item=self,
            blog_entry_items=blog_entry_items,
            tag=tag,
            item=self,
        )


@register
class BlogEntry(Default):
    itemtype = ITEMTYPE_BLOG_ENTRY
    display_name = L_("Blog entry")
    description = L_("Blog entry item")
    order = 0

    class _ModifyForm(Default._ModifyForm):
        meta_form = BlogEntryMetaForm
        meta_template = "blog/modify_entry_meta.html"

        @classmethod
        def from_item(cls, item):
            form = super().from_item(item)
            # preload PTIME with the current datetime
            if not form["meta_form"]["ptime"]:
                form["meta_form"]["ptime"].set(datetime.utcnow())
            return form

    def do_show(self, revid, **kwargs):
        blog_item_name = self.name.rsplit("/", 1)[0]
        try:
            blog_item = Item.create(blog_item_name)
        except AccessDenied:
            abort(403)
        if not isinstance(blog_item, Blog):
            # The parent item of this blog entry item is not a Blog item.
            abort(403)
        return render_template(
            "blog/entry.html",
            item_name=self.name,
            fqname=blog_item.fqname,
            blog_item=blog_item,
            blog_entry_item=self,
            item=self,
        )
