# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2004 by Florian Festi
# Copyright: 2006 by Mikko Virkkil
# Copyright: 2005-2010 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:ReimarBauer
# Copyright: 2008 MoinMoin:ChristopherDenter
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Wiki Utility Functions
"""

import os

from flask import current_app as app

import urllib

from moin.constants.contenttypes import CHARSET
from moin.constants.misc import URI_SCHEMES, CLEAN_INPUT_TRANSLATION_MAP, ITEM_INVALID_CHARS_REGEX
from moin.constants.contenttypes import DRAWING_EXTENSIONS

from moin.utils.mimetype import MimeType

from moin import log

logging = log.getLogger(__name__)


# constants for page names
PARENT_PREFIX = "../"
PARENT_PREFIX_LEN = len(PARENT_PREFIX)
CHILD_PREFIX = "/"
CHILD_PREFIX_LEN = len(CHILD_PREFIX)


#############################################################################
# Data validation / cleanup
#############################################################################


# TODO: use similar code in a flatland validator
def clean_input(text, max_len=201):
    """Clean input:
    replace CR, LF, TAB by whitespace
    delete control chars

    :param text: unicode text to clean (if we get str, we decode)
    :rtype: unicode
    :returns: cleaned text
    """
    # we only have input fields with max 200 chars, but spammers send us more
    length = len(text)
    if length == 0 or length > max_len:
        return ""
    else:
        if isinstance(text, bytes):
            # the translate() below can ONLY process unicode, thus, if we get
            # bytes, we try to decode it using the usual coding:
            text = text.decode(CHARSET)
        return text.translate(CLEAN_INPUT_TRANSLATION_MAP)


# TODO: use similar code in a flatland validator
def normalize_pagename(name, cfg):
    """Normalize page name

    Prevent creating page names with invisible characters or funny
    whitespace that might confuse the users or abuse the wiki, or
    just does not make sense.

    Restrict even more group pages, so they can be used inside acl lines.

    :param name: page name, unicode
    :rtype: unicode
    :returns: decoded and sanitized page name
    """
    # Strip invalid characters
    name = ITEM_INVALID_CHARS_REGEX.sub("", name)

    # Split to pages and normalize each one
    pages = name.split("/")
    normalized = []
    for page in pages:
        # Ignore empty or whitespace only pages
        if not page or page.isspace():
            continue

        # Cleanup group pages.
        # Strip non alpha numeric characters, keep white space
        if isGroupItem(page):
            page = "".join([c for c in page if c.isalnum() or c.isspace()])

        # Normalize white space. Each name can contain multiple
        # words separated with only one space. Split handle all
        # 30 unicode spaces (isspace() == True)
        page = " ".join(page.split())

        normalized.append(page)

    # Assemble components into full pagename
    name = "/".join(normalized)
    return name


#############################################################################
# Item types / Item names
#############################################################################


def isGroupItem(itemname):
    """Is this a name of group item?

    :param itemname: the item name
    :rtype: bool
    :returns: True if item is a group item
    """
    return app.cfg.cache.item_group_regexact.search(itemname) is not None


def AbsItemName(context, itemname):
    """
    Return the absolute item name for a (possibly) relative item name.

    :param context: name of the item where "itemname" appears on
    :param itemname: the (possibly relative) item name
    :rtype: unicode
    :returns: the absolute item name
    """
    if itemname.startswith(PARENT_PREFIX):
        while context and itemname.startswith(PARENT_PREFIX):
            context = "/".join(context.split("/")[:-1])
            itemname = itemname[PARENT_PREFIX_LEN:]
        itemname = "/".join([e for e in [context, itemname] if e])
    elif itemname.startswith(CHILD_PREFIX):
        if context:
            itemname = context + "/" + itemname[CHILD_PREFIX_LEN:]
        else:
            itemname = itemname[CHILD_PREFIX_LEN:]
    return itemname


def RelItemName(context, itemname):
    """
    Return the relative item name for some context.

    :param context: name of the item where "itemname" appears on
    :param itemname: the absolute item name
    :rtype: unicode
    :returns: the relative item name
    """
    if context == "":
        # special case, context is some "virtual root" item with name == ''
        # every item is a subitem of this virtual root
        return CHILD_PREFIX + itemname
    elif itemname.startswith(context + CHILD_PREFIX):
        # simple child
        return itemname[len(context) :]
    else:
        # some kind of sister/aunt
        context_frags = context.split("/")  # A, B, C, D, E
        itemname_frags = itemname.split("/")  # A, B, C, F
        # first throw away common parents:
        common = 0
        for cf, pf in zip(context_frags, itemname_frags):
            if cf == pf:
                common += 1
            else:
                break
        context_frags = context_frags[common:]  # D, E
        itemname_frags = itemname_frags[common:]  # F
        go_up = len(context_frags)
        return PARENT_PREFIX * go_up + "/".join(itemname_frags)


def ParentItemName(itemname):
    """
    Return the parent item name.

    :param itemname: the absolute item name (unicode)
    :rtype: unicode
    :returns: the parent item name (or empty string for toplevel items)
    """
    if itemname:
        pos = itemname.rfind("/")
        if pos > 0:
            return itemname[:pos]
    return ""


#############################################################################
# Misc
#############################################################################


def drawing2fname(drawing):
    _, ext = os.path.splitext(drawing)
    # note: do not just check for empty extension or stuff like drawing:foo.bar
    # will fail, instead of being expanded to foo.bar.svgdraw
    if ext not in DRAWING_EXTENSIONS:
        drawing += ".svgdraw"
    return drawing


def getUnicodeIndexGroup(name):
    """
    Return a group letter for `name`, which must be a unicode string.
    Currently supported: Hangul Syllables (U+AC00 - U+D7AF)

    :param name: a string
    :rtype: string
    :returns: group letter or None
    """
    c = name[0]
    if "\uAC00" <= c <= "\uD7AF":  # Hangul Syllables
        return chr(0xAC00 + (int(ord(c) - 0xAC00) / 588) * 588)
    else:
        return c.upper()  # we put lower and upper case words into the same index group


def is_URL(arg, schemes=URI_SCHEMES):
    """Return True if arg is a URL (with a scheme given in the schemes list).

    Note: there are not that many requirements for generic URLs, basically
    the only mandatory requirement is the ':' between scheme and rest.
    Scheme itself could be anything, also the rest (but we only support some
    schemes, as given in URI_SCHEMES, so it is a bit less ambiguous).
    """
    if ":" not in arg:
        return False
    for scheme in schemes:
        if arg.startswith(scheme + ":"):
            return True
    return False


def containsConflictMarker(text):
    """Returns true if there is a conflict marker in the text."""
    return "/!\\ '''Edit conflict" in text


def anchor_name_from_text(text):
    """
    Generate an anchor name from the given text.
    This function generates valid HTML IDs matching: [A-Za-z][A-Za-z0-9:_.-]*

    Note: this transformation has a special feature: when you feed it with a
    valid ID/name, it will return it without modification (identity
    transformation).
    """
    quoted = urllib.parse.quote_plus(text, safe=":", encoding="utf-7")
    res = quoted.replace("%", ".").replace("+", "_")
    if not res[:1].isalpha():
        return f"A{res}"
    return res


def split_anchor(pagename):
    """
    Split a pagename that (optionally) has an anchor into the real pagename
    and the anchor part. If there is no anchor, it returns an empty string
    for the anchor.

    Note: if pagename contains a # (as part of the pagename, not as anchor),
          you can use a trick to make it work nevertheless: just append a
          # at the end:
          "C##" returns ("C#", "")
          "Problem #1#" returns ("Problem #1", "")

    TODO: We shouldn't deal with composite pagename#anchor strings, but keep
          it separate.
          Current approach: [[pagename#anchor|label|attr=val,&qarg=qval]]
          Future approach:  [[pagename|label|attr=val,&qarg=qval,#anchor]]
          The future approach will avoid problems when there is a # in the
          pagename part (and no anchor). Also, we need to append #anchor
          at the END of the generated URL (AFTER the query string).
    """
    parts = pagename.rsplit("#", 1)
    if len(parts) == 2:
        return parts
    else:
        return pagename, ""


def get_hostname(addr):
    """
    Looks up the DNS hostname for some IP address.

    :param addr: IP address to look up (str)
    :returns: host dns name (unicode) or
              None (if lookup is disallowed or failed)
    """
    if app.cfg.log_reverse_dns_lookups:
        import socket

        try:
            return str(socket.gethostbyaddr(addr)[0], CHARSET)
        except (OSError, UnicodeError):
            pass


def file_headers(filename=None, content_type=None, content_length=None):
    """
    Compute http headers for sending a file

    :param filename: filename for autodetecting content_type (unicode, default: None)
    :param content_type: content-type header value (str, default: autodetect from filename)
    :param content_length: for content-length header (int, default:None)
    """
    if filename:
        # make sure we just have a simple filename (without path)
        filename = os.path.basename(filename)
        mt = MimeType(filename=filename)
    else:
        mt = None

    if content_type is None:
        if mt is not None:
            content_type = mt.content_type()
        else:
            content_type = "application/octet-stream"
    else:
        mt = MimeType(mimestr=content_type)

    headers = [("Content-Type", content_type)]
    if content_length is not None:
        headers.append(("Content-Length", str(content_length)))
    return headers
