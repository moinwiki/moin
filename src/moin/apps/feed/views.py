# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - feed views

    This contains all sort of feeds.
"""


from flask import request, Response
from flask import current_app as app
from flask import g as flaskg

from feedgen.feed import FeedGenerator
from markupsafe import Markup

from whoosh.query import Term, And

from moin.i18n import _
from moin.apps.feed import feed
from moin.constants.keys import (
    NAME,
    NAME_EXACT,
    NAMESPACE,
    WIKINAME,
    COMMENT,
    MTIME,
    REVID,
    ALL_REVS,
    PARENTID,
    LATEST_REVS,
)
from moin.themes import get_editor_info, render_template
from moin.items import Item
from moin.utils.crypto import cache_key
from moin.utils.interwiki import url_for_item, split_fqname

from moin import log

logging = log.getLogger(__name__)


@feed.route("/atom/<itemname:item_name>")
@feed.route("/atom", defaults=dict(item_name=""))
def atom(item_name):
    """
    Currently atom feeds behave in the following way
    - Text diffs are shown in a side-by-side fashion
    - The current binary item is fully rendered in the feed
    - Image(binary)'s diff is shown using PIL
    - First item is always rendered fully
    - Revision meta(id, size and comment) is shown for parent and current revision
    """
    query = Term(WIKINAME, app.cfg.interwikiname)
    if item_name:
        fqname = split_fqname(item_name)
        query = And([query, Term(NAME_EXACT, fqname.value), Term(NAMESPACE, fqname.namespace)])
    revs = list(flaskg.storage.search(query, idx_name=LATEST_REVS, sortedby=[MTIME], reverse=True, limit=1))
    if revs:
        rev = revs[0]
        cid = cache_key(usage="atom", revid=rev.revid, item_name=item_name)
        content = app.cache.get(cid)
    else:
        content = None
        cid = None
    if content is None:
        if not item_name:
            title = f"{app.cfg.sitename}"
        else:
            title = f"{app.cfg.sitename} - {fqname}"
        feed = FeedGenerator()
        feed.id(request.url)
        feed.title(title)
        feed.link(href=request.host_url)
        feed.link(href=request.url, rel="self")
        query = Term(WIKINAME, app.cfg.interwikiname)
        if item_name:
            query = And([query, Term(NAME_EXACT, fqname.value), Term(NAMESPACE, fqname.namespace)])
        history = flaskg.storage.search(query, idx_name=ALL_REVS, sortedby=[MTIME], reverse=True, limit=100)
        for rev in history:
            name = rev.fqname.fullname
            item = rev.item
            this_revid = rev.meta[REVID]
            logging.debug("name: %s revid: %s", name, this_revid)
            previous_revid = rev.meta.get(PARENTID)
            this_rev = rev
            try:
                hl_item = Item.create(name, rev_id=this_revid)
                if previous_revid is not None:
                    # HTML diff for subsequent revisions
                    previous_rev = item[previous_revid]
                    content = hl_item.content._render_data_diff_atom(
                        previous_rev, this_rev, fqname=this_rev.item.fqname
                    )
                else:
                    # full html rendering for new items
                    content = render_template(
                        "atom.html",
                        get="first_revision",
                        rev=this_rev,
                        content=Markup(hl_item.content._render_data()),
                        revision=this_revid,
                    )
            except Exception:
                logging.exception(f"content rendering crashed on item {name}")
                content = _("MoinMoin feels unhappy.")
            author = get_editor_info(rev.meta, external=True)
            rev_comment = rev.meta.get(COMMENT, "")
            if rev_comment:
                # Trim down extremely long revision comment
                if len(rev_comment) > 80:
                    content = render_template(
                        "atom.html", get="comment_cont_merge", comment=rev_comment[79:], content=Markup(content)
                    )
                    rev_comment = f"{rev_comment[:79]}..."
                feed_title = f"{author.get(NAME, '')} - {rev_comment}"
            else:
                feed_title = f"{author.get(NAME, '')}"
            if not item_name:
                feed_title = f"{name} - {feed_title}"
            feed_entry = feed.add_entry()
            feed_entry.id(url_for_item(name, rev=this_revid, _external=True))
            feed_entry.title(feed_title)
            feed_entry.author({"name": author.get(NAME, "")})
            feed_entry.link(href=url_for_item(name, rev=this_revid, _external=True))
            feed_entry.content(content, type="html")
        content = feed.atom_str(pretty=True).decode("utf-8")
        # Hack to add XSLT stylesheet declaration since AtomFeed doesn't allow this
        content = content.split("\n")
        content.insert(1, render_template("atom.html", get="xml"))
        content = "\n".join(content)
        if cid is not None:
            app.cache.set(cid, content)
    return Response(content, content_type="application/atom+xml")
