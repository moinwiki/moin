# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2025 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Miscellaneous views

Miscellaneous views that do not fit into another category.
"""

import time

from flask import Response
from flask import current_app as app
from flask import g as flaskg

from whoosh.query import Term, Or, And

from moin.apps.misc import misc

from moin.constants.keys import MTIME, NAME_EXACT, NAMESPACE, NAME
from moin.themes import render_template
from moin.utils.interwiki import CompositeName


@misc.route("/sitemap")
def sitemap():
    """
    XML sitemap for search engines.
    See https://www.sitemaps.org for usage details.
    """

    def format_timestamp(t):
        tm = time.gmtime(t)
        return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", tm)

    # get names for root urls
    root_fqnames = []
    root_mapping = [
        (namespace, app.cfg.root_mapping.get(namespace, app.cfg.default_root))
        for namespace, _ in app.cfg.namespace_mapping
    ]
    query = Or([And([Term(NAME_EXACT, root), Term(NAMESPACE, namespace)]) for namespace, root in root_mapping])
    for rev in flaskg.storage.search(q=query):
        root_fqnames.append(CompositeName(rev.meta[NAMESPACE], NAME_EXACT, rev.meta[NAME][0]))

    sitemap = []
    for rev in flaskg.storage.documents():
        fqnames = rev.fqnames
        mtime = rev.meta[MTIME]
        # default for content items:
        changefreq = "daily"
        priority = "0.5"
        for fqname in fqnames:
            if fqname in root_fqnames:
                # values for root items
                changefreq = "hourly"
                priority = "1.0"
            sitemap.append((fqname, format_timestamp(mtime), changefreq, priority))

    sitemap.sort()
    content = render_template("misc/sitemap.xml", sitemap=sitemap)
    return Response(content, mimetype="text/xml")


@misc.route("/urls_names")
def urls_names():
    """
    List of all item URLs and names, e.g., for SisterWiki.

    This view generates a list of item URLs and item names so that other wikis
    can implement SisterWiki functionality easily.
    See http://meatballwiki.org/wiki/SisterSitesImplementationGuide
    """
    # TODO: We currently also get deleted items; fix this.
    fq_names = []
    for rev in flaskg.storage.documents():
        fq_names += [fqname for fqname in rev.fqnames]
    content = render_template("misc/urls_names.txt", fq_names=fq_names)
    return Response(content, mimetype="text/plain")
