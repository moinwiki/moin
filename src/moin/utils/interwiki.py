# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:MicheleOrru
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - interwiki support code.
"""

from __future__ import annotations

from urllib.parse import quote as url_quote

from flask import current_app as app
from flask import url_for

import os.path

from moin.constants.keys import CURRENT, NAME_EXACT
from moin.constants.contenttypes import CHARSET
from moin.constants.namespaces import NAMESPACE_USERS
from moin.utils.names import get_fqname, split_fqname, split_namespace

from moin import log

logging = log.getLogger(__name__)


def is_local_wiki(wiki_name):
    """
    Check if <wiki_name> is this wiki.
    """
    return wiki_name in ["", "Self", app.cfg.interwikiname]


def is_known_wiki(wiki_name):
    """
    Check if <wiki_name> is a known wiki name.

    Note: interwiki_map should have entries for the special wikinames
    denoting THIS wiki, so we do not need to check these names separately.
    """
    return wiki_name in app.cfg.interwiki_map


def url_for_item(
    item_name: str,
    wiki_name: str = "",
    field: str = "",
    namespace: str = "",
    rev: str | None = CURRENT,
    endpoint: str = "frontend.show_item",
    _external: bool = False,
    regex: str = "",
):
    """
    Compute URL for some local or remote/interwiki item.

    For local items:
    Give <rev> to get the URL of a specific revision.
    Give <endpoint> to get the URL of a specific view,
    and give _external=True to compute fully specified URLs.

    For remote/interwiki items:
    If you just give <item_name> and <wiki_name>, a generic interwiki URL
    will be built.
    If you also give <rev> and/or <endpoint>, it is assumed that remote wiki
    URLs are built in the same way as local URLs.
    Computed URLs are always fully specified.
    """
    if field == NAME_EXACT:
        field = ""
    if is_local_wiki(wiki_name):
        item_name = get_fqname(item_name, field, namespace)
        if rev is None or rev == CURRENT:
            url = url_for(endpoint, item_name=item_name, _external=_external)
        else:
            url = url_for(endpoint, item_name=item_name, rev=rev, _external=_external)
    else:
        try:
            wiki_base_url = app.cfg.interwiki_map[wiki_name]
        except KeyError:
            logging.warning(f"no interwiki_map entry for {wiki_name!r}")
            item_name = get_fqname(item_name, field, namespace)
            if wiki_name:
                url = f"{wiki_name}/{item_name}"
            else:
                url = item_name
            url = f"/{url}"
        else:
            if (rev is None or rev == CURRENT) and endpoint == "frontend.show_item":
                # we just want to show latest revision (no special revision given) -
                # this is the generic interwiki url support, should work for any remote wiki
                url = join_wiki(wiki_base_url, item_name, field, namespace)
            else:
                # rev and/or endpoint was given, assume same URL building as for local wiki.
                # we need this for moin wiki farms, e.g. to link from search results to
                # some specific item/revision in another farm wiki.
                item_name = get_fqname(item_name, field, namespace)
                local_url = url_for(endpoint, item_name=item_name, rev=rev, _external=False)
                # we know that everything left of the + belongs to script url, but we
                # just want e.g. +show/42/FooBar to append it to the other wiki's
                # base URL.
                i = local_url.index("/+")
                path = local_url[i + 1 :]
                url = wiki_base_url + path
    if regex:
        url += f"?regex={url_quote(regex, encoding=CHARSET)}"
    return url


def get_download_file_name(fqname):
    """
    Return the filename used for downloading items.
    """
    if fqname.field == NAME_EXACT:
        return fqname.value
    else:
        return f"{fqname.field}-{fqname.value}"


def split_interwiki(wikiurl):
    """
    Split an interwiki name into wiki name and page name, e.g.::

        'MoinMoin/FrontPage' -> "MoinMoin", "", "", "FrontPage"
        'FrontPage' -> "Self", "", "", "FrontPage"
        'MoinMoin/Page with blanks' -> "MoinMoin", "", "", "Page with blanks"
        'MoinMoin/' -> "MoinMoin", "", "", ""
        'MoinMoin/@Someid/SomeValue' -> "MoinMoin", "", "Someid", "SomeValue" if Someid field exists or
                                        "MoinMoin", "", "", "Someid/SomePage" if not
        'MoinMoin/interwikins/AnyPage' -> "MoinMoin", "interwikins", "", "AnyPage"
        'ns/AnyPage' -> "Self", "ns", "", "AnyPage" if ns namespace exists or
                        "Self", "", "", "ns:AnyPage" if not.
        'ns1/ns2/AnyPage' -> "Self", "ns1/ns2", "", "AnyPage" if ns1/ns2 namespace exists OR
                             "Self", "ns1", "", "ns2/AnyPage" if ns1 namespace exists OR
                             "Self", "", "", "ns1/ns2/AnyPage" else.
        'MoinMoin/ns/@Somefield/AnyPage' ->
            "MoinMoin", "ns", "", "@Somefield/AnyPage" if ns namespace exists and field Somefield does not OR
            "MoinMoin", "ns", "Somefield", "AnyPage" if ns namespace and field Somefield exist OR
            "MoinMoin", "", "", "ns/@Somefield/AnyPage" else.
        :param wikiurl: the url to split
        :rtype: tuple
        :returns: (wikiname, namespace, field, pagename)
    """
    if not isinstance(wikiurl, str):
        wikiurl = wikiurl.decode("utf-8")
    # Base case: no colon in wikiurl
    if "/" not in wikiurl:
        return "Self", "", NAME_EXACT, wikiurl
    wikiname = field = namespace = ""
    if not wikiurl.startswith("/"):
        interwiki_mapping = set()
        for interwiki_name in app.cfg.interwiki_map:
            interwiki_mapping.add(interwiki_name.split("/")[0])
        wikiname, item_name = split_namespace(interwiki_mapping, wikiurl)
        if wikiname:
            wikiurl = wikiurl[len(wikiname) + 1 :]
        namespace, field, item_name = split_fqname(wikiurl)
        if not wikiname:
            wikiname = "Self"
        return wikiname, namespace, field, item_name
    else:
        namespace, field, item_name = split_fqname(wikiurl.split("/", 1)[1])
        return "Self", namespace, field, item_name


def join_wiki(wikiurl, wikitail, field, namespace):
    """
    Add a (URL-quoted) page name to an interwiki URL.

    Note: We can't know what kind of URL quoting a remote wiki expects.
          We just use a UTF-8 encoded string with standard URL quoting.

    :param wikiurl: wiki url, maybe including a $PAGE placeholder
    :param wikitail: page name
    :param namespace: namespace
    :rtype: string
    :returns: generated URL of the page in the other wiki
    """
    wikitail = url_quote(wikitail, encoding=CHARSET, safe="/")
    field = url_quote(field, encoding=CHARSET, safe="/")
    namespace = url_quote(namespace, encoding=CHARSET, safe="/")
    if not ("$PAGE" in wikiurl or "$NAMESPACE" in wikiurl or "$FIELD" in wikiurl):
        return wikiurl + get_fqname(wikitail, field, namespace)
    if "$PAGE" in wikiurl:
        wikiurl = wikiurl.replace("$PAGE", wikitail)
    if "$FIELD" in wikiurl:
        wikiurl = wikiurl.replace("$FIELD", field)
    if "$NAMESPACE" in wikiurl:
        wikiurl = wikiurl.replace("$NAMESPACE", namespace)
    return wikiurl


def getInterwikiName(item_name):
    """
    Get the (fully qualified) interwiki name of a local item name.

    :param item_name: item name (str)
    :rtype: str
    :returns: wiki_name:item_name
    """
    return f"{app.cfg.interwikiname}/{item_name}"


def getInterwikiHome(username):
    """
    Get a user's homepage.

    cfg.user_homewiki influences behavior:
    'Self' means we store user homepages in this wiki.
    When set to our own interwiki name, it behaves like 'Self'.

    'SomeOtherWiki' means we store user homepages in another wiki.

    :param username: the user's name
    :rtype: tuple
    :returns: (wikiname, itemname)
    """
    homewiki = app.cfg.user_homewiki
    if is_local_wiki(homewiki):
        homewiki = "Self"
    return homewiki, get_fqname(username, NAME_EXACT, NAMESPACE_USERS)


class InterWikiMap:
    """
    Parse a valid interwiki map file/string, transforming into a simple python dict
    object.
    Provides a set of utilities for parsing and checking a interwiki maps.
    """

    SKIP = "#"

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
                raise ValueError(f"malformed interwiki map string: {line}")

    @staticmethod
    def from_string(ustring):
        """
        Load and parse a valid interwiki map "str" object.
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
