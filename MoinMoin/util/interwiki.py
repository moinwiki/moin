# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:MicheleOrru
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - interwiki support code
"""

from __future__ import absolute_import, division

from werkzeug import url_quote

from flask import current_app as app

import os.path

from MoinMoin import config


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


def resolve_interwiki(wikiname, pagename):
    """ Resolve an interwiki reference (wikiname:pagename).

    Note: it is required that the interwiki_map contains entries for our
    own wikiname and also for 'Self' (same url):

    interwiki_map = {
        'Self': 'http://ourserver/ourpath/',
        'OurInterWikiName': 'http://ourserver/ourpath/',
        # other entries ...
    }

    :param wikiname: interwiki wiki name
    :param pagename: interwiki page name
    :rtype: tuple
    :returns: (wikitag, wikiurl, wikitail, err)
    """
    try:
        return (wikiname, app.cfg.interwiki_map[wikiname], pagename, False)
    except KeyError:
        return (wikiname, app.cfg.interwiki_map['Self'], "InterWiki", True)


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
    if homewiki == app.cfg.interwikiname:
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

