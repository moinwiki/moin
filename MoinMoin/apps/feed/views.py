# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:DiogenesAugusto
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - feed views

    This contains all sort of feeds.
"""


from datetime import datetime

from flask import request, Response
from flask import current_app as app
from flask import g as flaskg

from werkzeug.contrib.atom import AtomFeed

from whoosh.query import Term, And

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil
from MoinMoin.i18n import _, L_, N_
from MoinMoin.apps.feed import feed
from MoinMoin.config import (NAME, NAME_EXACT, WIKINAME, ACL, ACTION, ADDRESS,
                            HOSTNAME, USERID, COMMENT, MTIME, REVID, ALL_REVS,
                            PARENTID, LATEST_REVS)
from MoinMoin.themes import get_editor_info
from MoinMoin.items import Item
from MoinMoin.util.crypto import cache_key
from MoinMoin.util.interwiki import url_for_item

@feed.route('/atom/<itemname:item_name>')
@feed.route('/atom', defaults=dict(item_name=''))
def atom(item_name):
    # maybe we need different modes:
    # - diffs in html don't look great without stylesheet
    # - full item in html is nice
    # - diffs in textmode are OK, but look very simple
    # - full-item content in textmode is OK, but looks very simple
    query = Term(WIKINAME, app.cfg.interwikiname)
    if item_name:
        query = And([query, Term(NAME_EXACT, item_name), ])
    revs = list(flaskg.storage.search(query, idx_name=LATEST_REVS, sortedby=[MTIME], reverse=True, limit=1))
    if revs:
        rev = revs[0]
        cid = cache_key(usage="atom", revid=rev.revid, item_name=item_name)
        content = app.cache.get(cid)
    else:
        content = None
        cid = None
    if content is None:
        title = app.cfg.sitename
        feed = AtomFeed(title=title, feed_url=request.url, url=request.host_url)
        query = Term(WIKINAME, app.cfg.interwikiname)
        if item_name:
            query = And([query, Term(NAME_EXACT, item_name), ])
        history = flaskg.storage.search(query, idx_name=ALL_REVS, sortedby=[MTIME], reverse=True, limit=100)
        for rev in history:
            name = rev.meta[NAME]
            item = rev.item
            this_revid = rev.meta[REVID]
            previous_revid = rev.meta.get(PARENTID)
            this_rev = rev
            try:
                hl_item = Item.create(name, rev_id=this_revid)
                if previous_revid is not None:
                    # simple text diff for changes
                    previous_rev = item[previous_revid]
                    content = hl_item._render_data_diff_text(previous_rev.data, this_rev.data)
                    content = '<div><pre>{0}</pre></div>'.format(content)
                else:
                    # full html rendering for new items
                    content = hl_item._render_data()
                content_type = 'xhtml'
            except Exception as e:
                logging.exception("content rendering crashed")
                content = _(u'MoinMoin feels unhappy.')
                content_type = 'text'
            feed.add(title=name, title_type='text',
                     summary=rev.meta.get(COMMENT, ''), summary_type='text',
                     content=content, content_type=content_type,
                     author=get_editor_info(rev.meta, external=True),
                     url=url_for_item(name, rev=this_revid, _external=True),
                     updated=datetime.fromtimestamp(rev.meta[MTIME]),
                    )
        content = feed.to_string()
        if cid is not None:
            app.cache.set(cid, content)
    return Response(content, content_type='application/atom+xml')

