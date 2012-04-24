# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - miscellaneous views

    Misc. stuff that doesn't fit into another view category.
"""

import time

from flask import Response
from flask import current_app as app
from flask import g as flaskg

from MoinMoin.apps.misc import misc

from MoinMoin.config import NAME, MTIME
from MoinMoin.themes import render_template
from MoinMoin import wikiutil

SITEMAP_HAS_SYSTEM_ITEMS = True

@misc.route('/sitemap')
def sitemap():
    """
    Google (and others) XML sitemap
    """
    def format_timestamp(t):
        tm = time.gmtime(t)
        return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", tm)

    sitemap = []
    for rev in flaskg.storage.documents(wikiname=app.cfg.interwikiname):
        name = rev.meta[NAME]
        mtime = rev.meta[MTIME]
        if False: # was: wikiutil.isSystemItem(name)   XXX add back later, when we have that in the index
            if not SITEMAP_HAS_SYSTEM_ITEMS:
                continue
            # system items are rather boring
            changefreq = "yearly"
            priority = "0.1"
        else:
            # these are the content items:
            changefreq = "daily"
            priority = "0.5"
        sitemap.append((name, format_timestamp(mtime), changefreq, priority))
    # add an entry for root url
    root_item = app.cfg.item_root
    revs = list(flaskg.storage.documents(wikiname=app.cfg.interwikiname, name=root_item))
    if revs:
        mtime = revs[0].meta[MTIME]
        sitemap.append((u'', format_timestamp(mtime), "hourly", "1.0"))
    sitemap.sort()
    content = render_template('misc/sitemap.xml', sitemap=sitemap)
    return Response(content, mimetype='text/xml')


@misc.route('/urls_names')
def urls_names():
    """
    List of all item URLs and names, e.g. for sisteritems.

    This view generates a list of item URLs and item names, so that other wikis
    can implement SisterWiki functionality easily.
    See: http://usemod.com/cgi-bin/mb.pl?SisterSitesImplementationGuide
    """
    # XXX we currently also get deleted items, fix this
    item_names = sorted([rev.meta[NAME] for rev in flaskg.storage.documents(wikiname=app.cfg.interwikiname)])
    content = render_template('misc/urls_names.txt', item_names=item_names)
    return Response(content, mimetype='text/plain')

