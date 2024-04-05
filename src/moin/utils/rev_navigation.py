# Copyright: 2016 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    Helper function to get prior, current, next revisions and mod-times.
"""

from flask import g as flaskg
from flask import current_app as app
from flask import request
from whoosh.query import Term, And
from moin.constants.keys import ALL_REVS, CURRENT, MTIME, WIKINAME


def prior_next_revs(revid, fqname):
    """
    If viewing a revision other than the current revision,
    return prior, current, and next revids and time stamps else return None * 6.
    """
    try:
        show_revision = request.view_args["rev"] != CURRENT
    except KeyError:
        # maintenance scripts, such as dump-html, have request.view_args == {}
        show_revision = False
    if show_revision:
        terms = [Term(WIKINAME, app.cfg.interwikiname)]
        terms.extend(Term(term, value) for term, value in fqname.query.items())
        query = And(terms)
        revs = flaskg.storage.search(query, idx_name=ALL_REVS, sortedby=[MTIME], reverse=True, limit=None)
        rev_ids = []
        mtimes = []
        for rev in revs:
            mtimes.append(dict(rev.meta)["mtime"])
            rev_ids.append(rev.revid)
        prior_rev = next_rev = prior_mtime = next_mtime = None
        current_idx = rev_ids.index(revid)
        current_mtime = mtimes[current_idx]
        if current_idx:
            next_rev = rev_ids[current_idx - 1]
            next_mtime = mtimes[current_idx - 1]
        if current_idx < len(rev_ids) - 1:
            prior_rev = rev_ids[current_idx + 1]
            prior_mtime = mtimes[current_idx + 1]
        return (prior_rev, revid, next_rev, prior_mtime, current_mtime, next_mtime)
    return (None,) * 6
