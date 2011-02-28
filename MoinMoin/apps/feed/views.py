# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:DiogenesAugusto
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - feed views

    This contains all sort of feeds.
"""


from datetime import datetime

from flask import request, url_for, Response
from flask import flaskg

from flask import current_app as app

from werkzeug.contrib.atom import AtomFeed

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil
from MoinMoin.i18n import _, L_, N_
from MoinMoin.apps.feed import feed
from MoinMoin.items import NAME, ACL, MIMETYPE, ACTION, ADDRESS, HOSTNAME, USERID, COMMENT
from MoinMoin.themes import get_editor_info
from MoinMoin.items import Item

@feed.route('/atom/<itemname:item_name>')
@feed.route('/atom', defaults=dict(item_name=''))
def atom(item_name):
    # maybe we need different modes:
    # - diffs in html don't look great without stylesheet
    # - full item in html is nice
    # - diffs in textmode are OK, but look very simple
    # - full-item content in textmode is OK, but looks very simple
    cid = wikiutil.cache_key(usage="atom", item_name=item_name)
    content = app.cache.get(cid)
    if content is None:
        title = app.cfg.sitename
        feed = AtomFeed(title=title, feed_url=request.url, url=request.host_url)
        for rev in flaskg.storage.history(item_name=item_name):
            this_rev = rev
            this_revno = rev.revno
            item = rev.item
            name = rev[NAME]
            try:
                hl_item = Item.create(name, rev_no=this_revno)
                previous_revno = this_revno - 1
                if previous_revno >= 0:
                    # simple text diff for changes
                    previous_rev = item.get_revision(previous_revno)
                    content = hl_item._render_data_diff_text(previous_rev, this_rev)
                    content = '<div><pre>%s</pre></div>' % content
                else:
                    # full html rendering for new items
                    content = hl_item._render_data()
                content_type = 'xhtml'
            except Exception, e:
                logging.exception("content rendering crashed")
                content = _(u'MoinMoin feels unhappy.')
                content_type = 'text'
            feed.add(title=name, title_type='text',
                     summary=rev.get(COMMENT, ''), summary_type='text',
                     content=content, content_type=content_type,
                     author=get_editor_info(rev, external=True),
                     url=url_for('frontend.show_item', item_name=name, rev=this_revno, _external=True),
                     updated=datetime.utcfromtimestamp(rev.timestamp),
                    )
        content = feed.to_string()
        app.cache.set(cid, content)
    return Response(content, content_type='application/atom+xml')

