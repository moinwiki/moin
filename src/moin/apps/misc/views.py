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

from whoosh.query import Term, Or, And

from moin.apps.misc import misc

from moin.constants.keys import MTIME, NAME_EXACT, NAMESPACE
from moin.themes import render_template


@misc.route("/sitemap")
def sitemap():
    """
    Google (and others) XML sitemap
    """

    def format_timestamp(t):
        tm = time.gmtime(t)
        return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", tm)

    sitemap = []
    for rev in flaskg.storage.documents(wikiname=app.cfg.interwikiname):
        fqnames = rev.fqnames
        mtime = rev.meta[MTIME]
        # these are the content items:
        changefreq = "daily"
        priority = "0.5"
        sitemap += [(fqname, format_timestamp(mtime), changefreq, priority) for fqname in fqnames]
    # add entries for root urls
    root_mapping = [
        (namespace, app.cfg.root_mapping.get(namespace, app.cfg.default_root))
        for namespace, _ in app.cfg.namespace_mapping
    ]
    query = Or([And([Term(NAME_EXACT, root), Term(NAMESPACE, namespace)]) for namespace, root in root_mapping])
    for rev in flaskg.storage.search(q=query):
        mtime = rev.meta[MTIME]
        sitemap.append((rev.meta[NAMESPACE], format_timestamp(mtime), "hourly", "1.0"))
    sitemap.sort()
    content = render_template("misc/sitemap.xml", sitemap=sitemap)
    return Response(content, mimetype="text/xml")


@misc.route("/urls_names")
def urls_names():
    """
    List of all item URLs and names, e.g. for sisteritems.

    This view generates a list of item URLs and item names, so that other wikis
    can implement SisterWiki functionality easily.
    See: http://meatballwiki.org/wiki/SisterSitesImplementationGuide
    """
    # XXX we currently also get deleted items, fix this
    fq_names = []
    for rev in flaskg.storage.documents(wikiname=app.cfg.interwikiname):
        fq_names += [fqname for fqname in rev.fqnames]
    content = render_template("misc/urls_names.txt", fq_names=fq_names)
    return Response(content, mimetype="text/plain")
