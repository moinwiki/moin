# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:MicheleOrru
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - interwiki support code
"""

from urllib.parse import quote as url_quote

from flask import current_app as app
from flask import url_for

import os.path
from collections import namedtuple

from moin.constants.keys import CURRENT, FIELDS, NAME_EXACT, NAMESPACE
from moin.constants.contenttypes import CHARSET

from moin import log

logging = log.getLogger(__name__)


def is_local_wiki(wiki_name):
    """
    check if <wiki_name> is THIS wiki
    """
    return wiki_name in ["", "Self", app.cfg.interwikiname]


def is_known_wiki(wiki_name):
    """
    check if <wiki_name> is a known wiki name

    Note: interwiki_map should have entries for the special wikinames
    denoting THIS wiki, so we do not need to check these names separately.
    """
    return wiki_name in app.cfg.interwiki_map


def get_fqname(item_name, field, namespace):
    """
    Compute composite name from item_name, field, namespace
    composite name == [NAMESPACE/][@FIELD/]NAME
    """
    if field and field != NAME_EXACT:
        item_name = f"@{field}/{item_name}"
    if namespace:
        item_name = f"{namespace}/{item_name}"
    return item_name


def url_for_item(
    item_name,
    wiki_name="",
    field="",
    namespace="",
    rev=CURRENT,
    endpoint="frontend.show_item",
    _external=False,
    regex="",
):
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
    returns the filename that is used for downloading items
    """
    if fqname.field == NAME_EXACT:
        return fqname.value
    else:
        return f"{fqname.field}-{fqname.value}"


def _split_namespace(namespaces, url):
    """
    Find the longest namespace in the set.
    the namespaces are separated by  slashes (/).
    Example:
        namespaces_set(['ns1', 'ns1/ns2'])
        url: ns1/urlalasd return: ns1, urlalasd
        url: ns3/urlalasd return: '', ns3/urlalasd
        url: ns2/urlalasd return: '', ns2/urlalasd
        url: ns1/ns2/urlalasd return: ns1/ns2, urlalasd
    param namespaces_set: set of namespaces (strings) to search
    param url: string
    returns: (namespace, url)
    """
    namespace = ""
    tokens_list = url.split("/")
    for token in tokens_list:
        if namespace:
            token = f"{namespace}/{token}"
        if token in namespaces:
            namespace = token
        else:
            break
    if namespace:
        length = len(namespace) + 1
        url = url[length:]
    return namespace, url


class CompositeName(namedtuple("CompositeName", "namespace, field, value")):
    """
    namedtuple to hold the compositename
    """

    @property
    def split(self):
        """
        returns a dict of field_names/field_values
        """
        return {NAMESPACE: self.namespace, "field": self.field, "item_name": self.value}

    @property
    def fullname(self):
        return get_fqname(self.value, self.field, self.namespace)

    def __str__(self):
        return self.fullname

    @property
    def query(self):
        """
        returns a dict that can be used as a whoosh query
        to lookup index documents matching this CompositeName
        """
        field = NAME_EXACT if not self.field else self.field
        return {NAMESPACE: self.namespace, field: self.value}

    def get_root_fqname(self):
        """
        Set value to the item_root of that namespace, and return
        the new CompositeName.
        """
        return CompositeName(self.namespace, NAME_EXACT, app.cfg.root_mapping.get(self.namespace, app.cfg.default_root))


def split_fqname(url):
    """
    Split a fully qualified url into namespace, field and pagename
    url -> [NAMESPACE/][@FIELD/]NAME

    :param url: the url to split
    :returns: a namedtuple CompositeName(namespace, field, itemname)
    Examples::

        url: 'ns1/ns2/@itemid/Page' return 'ns1/ns2', 'itemid', 'Page'
        url: '@revid/OtherPage' return '', 'revid', 'OtherPage'
        url: 'ns1/Page' return 'ns1', '', 'Page'
        url: 'ns1/ns2/@notfield' return 'ns1/ns2', '', '@notfield'
    """
    if not url:
        return CompositeName("", NAME_EXACT, "")
    namespaces = {namespace.rstrip("/") for namespace, _ in app.cfg.namespace_mapping}
    namespace, url = _split_namespace(namespaces, url)
    field = NAME_EXACT
    if url.startswith("@"):
        tokens = url[1:].split("/", 1)
        if tokens[0] in FIELDS:
            field = tokens[0]
            url = tokens[1] if len(tokens) > 1 else ""
    return CompositeName(namespace, field, url)


def split_interwiki(wikiurl):
    """
    Split a interwiki name, into wikiname and pagename, e.g::

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
        wikiname, item_name = _split_namespace(interwiki_mapping, wikiurl)
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
    Add a (url_quoted) page name to an interwiki url.

    Note: We can't know what kind of URL quoting a remote wiki expects.
          We just use a utf-8 encoded string with standard URL quoting.

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
        homewiki = "Self"
    return homewiki, username


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
