# -*- coding: utf-8 -*-
"""
    MoinMoin - miscellaneous views

    Misc. stuff that doesn't fit into another view category.

    @copyright: 2010 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

import time

from flask import Response
from flask import flaskg

from flask import current_app as app

from MoinMoin.apps.misc import misc

from MoinMoin.themes import render_template
from MoinMoin import wikiutil
from MoinMoin.storage.error import NoSuchRevisionError, NoSuchItemError

SITEMAP_HAS_SYSTEM_ITEMS = True

@misc.route('/sitemap')
def sitemap():
    """
    Google (and others) XML sitemap
    """
    def format_timestamp(ts):
        return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(ts))

    sitemap = []
    for item in flaskg.storage.iteritems():
        try:
            rev = item.get_revision(-1)
        except NoSuchRevisionError:
            # XXX we currently also get user items, they have no revisions -
            # but in the end, they should not be readable by the user anyways
            continue
        if wikiutil.isSystemItem(item.name):
            if not SITEMAP_HAS_SYSTEM_ITEMS:
                continue
            # system items are rather boring
            changefreq = "yearly"
            priority = "0.1"
        else:
            # these are the content items:
            changefreq = "daily"
            priority = "0.5"
        sitemap.append((item.name, format_timestamp(rev.timestamp), changefreq, priority))
    # add an entry for root url
    try:
        item = flaskg.storage.get_item(app.cfg.item_root)
        rev = item.get_revision(-1)
        sitemap.append((u'', format_timestamp(rev.timestamp), "hourly", "1.0"))
    except NoSuchItemError:
        pass
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
    # XXX we currently also get user items, fix this
    item_names = [item.name for item in flaskg.storage.iteritems()]
    item_names.sort()
    content = render_template('misc/urls_names.txt', item_names=item_names)
    return Response(content, mimetype='text/plain')

