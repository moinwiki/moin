# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:MicheleOrru
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - interwiki support code
"""

from __future__ import absolute_import, division

from werkzeug import url_quote

from flask import current_app as app
from flask import url_for

import os.path

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import config


def is_local_wiki(wiki_name):
    """
    check if <wiki_name> is THIS wiki
    """
    return wiki_name in ['', 'Self', app.cfg.interwikiname, ]


def is_known_wiki(wiki_name):
    """
    check if <wiki_name> is a known wiki name

    Note: interwiki_map should have entries for the special wikinames
    denoting THIS wiki, so we do not need to check these names separately.
    """
    return wiki_name in app.cfg.interwiki_map


def url_for_item(item_name, wiki_name='', rev=-1, endpoint='frontend.show_item', _external=False):
    """
    Compute URL for some local or remote/interwiki item.

    For local items:
    give <rev> to get the url of some specific revision.
    give the <endpoint> to get the url of some specific view,
    give _external=True to compute fully specified URLs.

    For remote/interwiki items:
    If you just give <item_name> and <wiki_name>, a generic interwiki URL
    will be built.
    If you also give <rev> and/or <endpoint>, it is assumed that remote wiki
    URLs are built in the same way as local URLs.
    Computed URLs are always fully specified.
    """
    if is_local_wiki(wiki_name):
        if rev is None or rev == -1:
            url = url_for(endpoint, item_name=item_name, _external=_external)
        else:
            url = url_for(endpoint, item_name=item_name, rev=rev, _external=_external)
    else:
        try:
            wiki_base_url = app.cfg.interwiki_map[wiki_name]
        except KeyError, err:
            logging.warning("no interwiki_map entry for %r" % wiki_name)
            url = '' # can we find something useful?
        else:
            if (rev is None or rev == -1) and endpoint == 'frontend.show_item':
                # we just want to show latest revision (no special revision given) -
                # this is the generic interwiki url support, should work for any remote wiki
                url = join_wiki(wiki_base_url, item_name)
            else:
                # rev and/or endpoint was given, assume same URL building as for local wiki.
                # we need this for moin wiki farms, e.g. to link from search results to
                # some specific item/revision in another farm wiki.
                local_url = url_for(endpoint, item_name=item_name, rev=rev, _external=False)
                # we know that everything left of the + belongs to script url, but we
                # just want e.g. +show/42/FooBar to append it to the other wiki's
                # base URL.
                i = local_url.index('/+')
                path = local_url[i+1:]
                url = wiki_base_url + path
    return url


def split_interwiki(wikiurl):
    """ Split a interwiki name, into wikiname and pagename, e.g:

    'MoinMoin:FrontPage' -> "MoinMoin", "FrontPage"
    'FrontPage' -> "Self", "FrontPage"
    'MoinMoin:Page with blanks' -> "MoinMoin", "Page with blanks"
    'MoinMoin:' -> "MoinMoin", ""

    :param wikiurl: the url to split
    :rtype: tuple
    :returns: (wikiname, pagename)
    """
    try:
        wikiname, pagename = wikiurl.split(":", 1)
    except ValueError:
        wikiname, pagename = 'Self', wikiurl
    return wikiname, pagename


def join_wiki(wikiurl, wikitail):
    """
    Add a (url_quoted) page name to an interwiki url.

    Note: We can't know what kind of URL quoting a remote wiki expects.
          We just use a utf-8 encoded string with standard URL quoting.

    :param wikiurl: wiki url, maybe including a $PAGE placeholder
    :param wikitail: page name
    :rtype: string
    :returns: generated URL of the page in the other wiki
    """
    wikitail = url_quote(wikitail, charset=config.charset, safe='/')
    if '$PAGE' in wikiurl:
        return wikiurl.replace('$PAGE', wikitail)
    else:
        return wikiurl + wikitail


def getInterwikiName(item_name):
    """
    Get the (fully qualified) interwiki name of a local item name.

    :param item_ame: item name (unicode)
    :rtype: unicode
    :returns: wiki_name:item_name
    """
    return "%s:%s" % (app.cfg.interwikiname, item_name)


def getInterwikiHome(username):
    """
    Get a user's homepage.

    cfg.user_homewiki influences behaviour of this:
    'Self' does mean we store user homepage in THIS wiki.
    When set to our own interwikiname, it behaves like with 'Self'.

    'SomeOtherWiki' means we store user homepages in another wiki.

    :param username: the user's name
    :rtype: tuple
    :returns: (wikiname, itemname)
    """
    homewiki = app.cfg.user_homewiki
    if is_local_wiki(homewiki):
        homewiki = u'Self'
    return homewiki, username


class InterWikiMap(object):
    """
    Parse a valid interwiki map file/string, transforming into a simple python dict
    object.
    Provides a set of utilities for parsing and checking a interwiki maps.
    """

    SKIP = '#'

    def __init__(self, s):
        """
        Check for 's' to be a valid interwiki map string,
        then  parses it and stores to a dict.
        """
        self.iwmap = dict()

        for line in s.splitlines():
            if self.SKIP in line:
                line = line.split(self.SKIP, 1)[0]
            # remove trailing spaces (if any)
            line = line.rstrip()
            if not line:
                continue

            try:
                name, url = line.split(None, 1)
                self.iwmap[name] = url
            except ValueError:
                raise ValueError('malformed interwiki map string: {0}'.format(
                                 line))

    @staticmethod
    def from_string(ustring):
        """
        Load and parse a valid interwiki map "unicode" object.
        """
        return InterWikiMap(ustring)

    @staticmethod
    def from_file(filename):
        """
        Load and parse a valid interwiki map file.
        """
        filename = os.path.expanduser(filename)
        with open(filename) as f:
            parser = InterWikiMap(f.read())

        return parser

