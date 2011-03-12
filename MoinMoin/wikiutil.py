# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2004 by Florian Festi
# Copyright: 2006 by Mikko Virkkil
# Copyright: 2005-2010 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:ReimarBauer
# Copyright: 2008 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Wiki Utility Functions
"""


import os
import re
import time
import hashlib

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app
from flask import flaskg
from flask import request

from MoinMoin import config
from MoinMoin.config import IS_SYSITEM

from MoinMoin.i18n import _, L_, N_
from MoinMoin.util import pysupport, lock
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError

import werkzeug

# constants for page names
PARENT_PREFIX = "../"
PARENT_PREFIX_LEN = len(PARENT_PREFIX)
CHILD_PREFIX = "/"
CHILD_PREFIX_LEN = len(CHILD_PREFIX)

#############################################################################
### Getting data from user/Sending data to user
#############################################################################

def decodeUnknownInput(text):
    """ Decode input in unknown encoding

    First we try utf-8 because it has special format, and it will decode
    only utf-8 files. Then we try config.charset, then iso-8859-1 using
    'replace'. We will never raise an exception, but may return junk
    data.

    WARNING: Use this function only for data that you view, not for data
    that you save in the wiki.

    :param text: the text to decode, string
    :rtype: unicode
    :returns: decoded text (maybe wrong)
    """
    # Shortcut for unicode input
    if isinstance(text, unicode):
        return text

    try:
        return unicode(text, 'utf-8')
    except UnicodeError:
        if config.charset not in ['utf-8', 'iso-8859-1']:
            try:
                return unicode(text, config.charset)
            except UnicodeError:
                pass
        return unicode(text, 'iso-8859-1', 'replace')


def decodeUserInput(s, charsets=[config.charset]):
    """
    Decodes input from the user.

    :param s: the string to unquote
    :param charsets: list of charsets to assume the string is in
    :rtype: unicode
    :returns: the unquoted string as unicode
    """
    for charset in charsets:
        try:
            return s.decode(charset)
        except UnicodeError:
            pass
    raise UnicodeError('The string %r cannot be decoded.' % s)


def clean_input(text, max_len=201):
    """ Clean input:
        replace CR, LF, TAB by whitespace
        delete control chars

        :param text: unicode text to clean (if we get str, we decode)
        :rtype: unicode
        :returns: cleaned text
    """
    # we only have input fields with max 200 chars, but spammers send us more
    length = len(text)
    if length == 0 or length > max_len:
        return u''
    else:
        if isinstance(text, str):
            # the translate() below can ONLY process unicode, thus, if we get
            # str, we try to decode it using the usual coding:
            text = text.decode(config.charset)
        return text.translate(config.clean_input_translation_map)


def make_breakable(text, maxlen):
    """ make a text breakable by inserting spaces into nonbreakable parts
    """
    text = text.split(" ")
    newtext = []
    for part in text:
        if len(part) > maxlen:
            while part:
                newtext.append(part[:maxlen])
                part = part[maxlen:]
        else:
            newtext.append(part)
    return " ".join(newtext)


#############################################################################
### Item types (based on item names)
#############################################################################

def isSystemItem(itemname):
    """ Is this a system page?

    :param itemname: the item name
    :rtype: bool
    :returns: True if page is a system item
    """
    try:
        item = flaskg.storage.get_item(itemname)
        return item.get_revision(-1)[IS_SYSITEM]
    except (NoSuchItemError, NoSuchRevisionError, KeyError):
        pass

    return False


def isGroupItem(itemname):
    """ Is this a name of group item?

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
            context = '/'.join(context.split('/')[:-1])
            itemname = itemname[PARENT_PREFIX_LEN:]
        itemname = '/'.join(filter(None, [context, itemname, ]))
    elif itemname.startswith(CHILD_PREFIX):
        if context:
            itemname = context + '/' + itemname[CHILD_PREFIX_LEN:]
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
    if context == '':
        # special case, context is some "virtual root" item with name == ''
        # every item is a subitem of this virtual root
        return CHILD_PREFIX + itemname
    elif itemname.startswith(context + CHILD_PREFIX):
        # simple child
        return itemname[len(context):]
    else:
        # some kind of sister/aunt
        context_frags = context.split('/')   # A, B, C, D, E
        itemname_frags = itemname.split('/') # A, B, C, F
        # first throw away common parents:
        common = 0
        for cf, pf in zip(context_frags, itemname_frags):
            if cf == pf:
                common += 1
            else:
                break
        context_frags = context_frags[common:] # D, E
        itemname_frags = itemname_frags[common:] # F
        go_up = len(context_frags)
        return PARENT_PREFIX * go_up + '/'.join(itemname_frags)


def ParentItemName(itemname):
    """
    Return the parent item name.

    :param itemname: the absolute item name (unicode)
    :rtype: unicode
    :returns: the parent item name (or empty string for toplevel items)
    """
    if itemname:
        pos = itemname.rfind('/')
        if pos > 0:
            return itemname[:pos]
    return u''


#############################################################################
### mimetype support
#############################################################################
import mimetypes

MIMETYPES_MORE = {
 # OpenOffice 2.x & other open document stuff
 '.odt': 'application/vnd.oasis.opendocument.text',
 '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
 '.odp': 'application/vnd.oasis.opendocument.presentation',
 '.odg': 'application/vnd.oasis.opendocument.graphics',
 '.odc': 'application/vnd.oasis.opendocument.chart',
 '.odf': 'application/vnd.oasis.opendocument.formula',
 '.odb': 'application/vnd.oasis.opendocument.database',
 '.odi': 'application/vnd.oasis.opendocument.image',
 '.odm': 'application/vnd.oasis.opendocument.text-master',
 '.ott': 'application/vnd.oasis.opendocument.text-template',
 '.ots': 'application/vnd.oasis.opendocument.spreadsheet-template',
 '.otp': 'application/vnd.oasis.opendocument.presentation-template',
 '.otg': 'application/vnd.oasis.opendocument.graphics-template',
 # some systems (like Mac OS X) don't have some of these:
 '.patch': 'text/x-diff',
 '.diff': 'text/x-diff',
 '.py': 'text/x-python',
 '.cfg': 'text/plain',
 '.conf': 'text/plain',
 '.irc': 'text/plain',
 '.md5': 'text/plain',
 '.csv': 'text/csv',
 '.flv': 'video/x-flv',
 '.wmv': 'video/x-ms-wmv',
 '.swf': 'application/x-shockwave-flash',
 '.moin': 'text/x.moin.wiki',
 '.creole': 'text/x.moin.creole',
}

# add all mimetype patterns of pygments
import pygments.lexers

for name, short, patterns, mime in pygments.lexers.get_all_lexers():
    for pattern in patterns:
        if pattern.startswith('*.') and mime:
            MIMETYPES_MORE[pattern[1:]] = mime[0]

[mimetypes.add_type(mimetype, ext, True) for ext, mimetype in MIMETYPES_MORE.items()]

MIMETYPES_sanitize_mapping = {
    # this stuff is text, but got application/* for unknown reasons
    ('application', 'docbook+xml'): ('text', 'docbook'),
    ('application', 'x-latex'): ('text', 'latex'),
    ('application', 'x-tex'): ('text', 'tex'),
    ('application', 'javascript'): ('text', 'javascript'),
}

MIMETYPES_spoil_mapping = {} # inverse mapping of above
for _key, _value in MIMETYPES_sanitize_mapping.items():
    MIMETYPES_spoil_mapping[_value] = _key


class MimeType(object):
    """ represents a mimetype like text/plain """

    def __init__(self, mimestr=None, filename=None):
        self.major = self.minor = None # sanitized mime type and subtype
        self.params = {} # parameters like "charset" or others
        self.charset = None # this stays None until we know for sure!
        self.raw_mimestr = mimestr
        self.filename = filename
        if mimestr:
            self.parse_mimetype(mimestr)
        elif filename:
            self.parse_filename(filename)

    def parse_filename(self, filename):
        mtype, encoding = mimetypes.guess_type(filename)
        if mtype is None:
            mtype = 'application/octet-stream'
        self.parse_mimetype(mtype)

    def parse_mimetype(self, mimestr):
        """ take a string like used in content-type and parse it into components,
            alternatively it also can process some abbreviated string like "wiki"
        """
        parameters = mimestr.split(";")
        parameters = [p.strip() for p in parameters]
        mimetype, parameters = parameters[0], parameters[1:]
        mimetype = mimetype.split('/')
        if len(mimetype) >= 2:
            major, minor = mimetype[:2] # we just ignore more than 2 parts
        else:
            major, minor = self.parse_format(mimetype[0])
        self.major = major.lower()
        self.minor = minor.lower()
        for param in parameters:
            key, value = param.split('=')
            if value[0] == '"' and value[-1] == '"': # remove quotes
                value = value[1:-1]
            self.params[key.lower()] = value
        if 'charset' in self.params:
            self.charset = self.params['charset'].lower()
        self.sanitize()

    def parse_format(self, format):
        """ maps from what we currently use on-page in a #format xxx processing
            instruction to a sanitized mimetype major, minor tuple.
            can also be user later for easier entry by the user, so he can just
            type "wiki" instead of "text/x.moin.wiki".
        """
        format = format.lower()
        if format in config.parser_text_mimetype:
            mimetype = 'text', format
        else:
            mapping = {
                'wiki': ('text', 'x.moin.wiki'),
                'irc': ('text', 'irssi'),
            }
            try:
                mimetype = mapping[format]
            except KeyError:
                mimetype = 'text', 'x-%s' % format
        return mimetype

    def sanitize(self):
        """ convert to some representation that makes sense - this is not necessarily
            conformant to /etc/mime.types or IANA listing, but if something is
            readable text, we will return some ``text/*`` mimetype, not ``application/*``,
            because we need text/plain as fallback and not application/octet-stream.
        """
        self.major, self.minor = MIMETYPES_sanitize_mapping.get((self.major, self.minor), (self.major, self.minor))

    def spoil(self):
        """ this returns something conformant to /etc/mime.type or IANA as a string,
            kind of inverse operation of sanitize(), but doesn't change self
        """
        major, minor = MIMETYPES_spoil_mapping.get((self.major, self.minor), (self.major, self.minor))
        return self.content_type(major, minor)

    def content_type(self, major=None, minor=None, charset=None, params=None):
        """ return a string suitable for Content-Type header
        """
        major = major or self.major
        minor = minor or self.minor
        params = params or self.params or {}
        if major == 'text':
            charset = charset or self.charset or params.get('charset', config.charset)
            params['charset'] = charset
        mimestr = "%s/%s" % (major, minor)
        params = ['%s="%s"' % (key.lower(), value) for key, value in params.items()]
        params.insert(0, mimestr)
        return "; ".join(params)

    def mime_type(self):
        """ return a string major/minor only, no params """
        return "%s/%s" % (self.major, self.minor)

    def content_disposition(self, cfg):
        # for dangerous files (like .html), when we are in danger of cross-site-scripting attacks,
        # we just let the user store them to disk ('attachment').
        # For safe files, we directly show them inline (this also works better for IE).
        mime_type = self.mime_type()
        dangerous = mime_type in cfg.mimetypes_xss_protect
        content_disposition = dangerous and 'attachment' or 'inline'
        filename = self.filename
        if filename is not None:
            # TODO: fix the encoding here, plain 8 bit is not allowed according to the RFCs
            # There is no solution that is compatible to IE except stripping non-ascii chars
            if isinstance(filename, unicode):
                filename = filename.encode(config.charset)
            content_disposition += '; filename="%s"' % filename
        return content_disposition

    def module_name(self):
        """ convert this mimetype to a string useable as python module name,
            we yield the exact module name first and then proceed to shorter
            module names (useful for falling back to them, if the more special
            module is not found) - e.g. first "text_python", next "text".
            Finally, we yield "application_octet_stream" as the most general
            mimetype we have.

            Hint: the fallback handler module for text/* should be implemented
            in module "text" (not "text_plain")
        """
        mimetype = self.mime_type()
        modname = mimetype.replace("/", "_").replace("-", "_").replace(".", "_")
        fragments = modname.split('_')
        for length in range(len(fragments), 1, -1):
            yield "_".join(fragments[:length])
        yield self.raw_mimestr
        yield fragments[0]
        yield "application_octet_stream"


#############################################################################
### Misc
#############################################################################
def normalize_pagename(name, cfg):
    """ Normalize page name

    Prevent creating page names with invisible characters or funny
    whitespace that might confuse the users or abuse the wiki, or
    just does not make sense.

    Restrict even more group pages, so they can be used inside acl lines.

    :param name: page name, unicode
    :rtype: unicode
    :returns: decoded and sanitized page name
    """
    # Strip invalid characters
    name = config.page_invalid_chars_regex.sub(u'', name)

    # Split to pages and normalize each one
    pages = name.split(u'/')
    normalized = []
    for page in pages:
        # Ignore empty or whitespace only pages
        if not page or page.isspace():
            continue

        # Cleanup group pages.
        # Strip non alpha numeric characters, keep white space
        if isGroupItem(page):
            page = u''.join([c for c in page
                             if c.isalnum() or c.isspace()])

        # Normalize white space. Each name can contain multiple
        # words separated with only one space. Split handle all
        # 30 unicode spaces (isspace() == True)
        page = u' '.join(page.split())

        normalized.append(page)

    # Assemble components into full pagename
    name = u'/'.join(normalized)
    return name


def drawing2fname(drawing):
    config.drawing_extensions = ['.tdraw', '.adraw',
                                 '.svg',
                                 '.png', '.jpg', '.jpeg', '.gif',
                                ]
    fname, ext = os.path.splitext(drawing)
    # note: do not just check for empty extension or stuff like drawing:foo.bar
    # will fail, instead of being expanded to foo.bar.tdraw
    if ext not in config.drawing_extensions:
        # for backwards compatibility, twikidraw is the default:
        drawing += '.tdraw'
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
    if u'\uAC00' <= c <= u'\uD7AF': # Hangul Syllables
        return unichr(0xac00 + (int(ord(c) - 0xac00) / 588) * 588)
    else:
        return c.upper() # we put lower and upper case words into the same index group


def is_URL(arg, schemas=config.url_schemas):
    """ Return True if arg is a URL (with a schema given in the schemas list).

        Note: there are not that many requirements for generic URLs, basically
        the only mandatory requirement is the ':' between schema and rest.
        Schema itself could be anything, also the rest (but we only support some
        schemas, as given in config.url_schemas, so it is a bit less ambiguous).
    """
    if ':' not in arg:
        return False
    for schema in schemas:
        if arg.startswith(schema + ':'):
            return True
    return False


def containsConflictMarker(text):
    """ Returns true if there is a conflict marker in the text. """
    return "/!\\ '''Edit conflict" in text

def anchor_name_from_text(text):
    """
    Generate an anchor name from the given text.
    This function generates valid HTML IDs matching: [A-Za-z][A-Za-z0-9:_.-]*

    Note: this transformation has a special feature: when you feed it with a
    valid ID/name, it will return it without modification (identity
    transformation).
    """
    quoted = werkzeug.url_quote_plus(text, charset='utf-7', safe=':')
    res = quoted.replace('%', '.').replace('+', '_')
    if not res[:1].isalpha():
        return 'A%s' % res
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
    parts = pagename.rsplit('#', 1)
    if len(parts) == 2:
        return parts
    else:
        return pagename, ""


def get_hostname(addr):
    """
    Looks up the hostname depending on the configuration.
    """
    if app.cfg.log_reverse_dns_lookups:
        import socket
        try:
            hostname = socket.gethostbyaddr(addr)[0]
            hostname = unicode(hostname, config.charset)
        except (socket.error, UnicodeError):
            hostname = addr
    else:
        hostname = addr
    return hostname


def file_headers(filename=None,
                 content_type=None, content_length=None, content_disposition=None):
        """
        Compute http headers for sending a file

        :param filename: filename for content-disposition header and for autodetecting
                         content_type (unicode, default: None)
        :param content_type: content-type header value (str, default: autodetect from filename)
        :param content_disposition: type for content-disposition header (str, default: None)
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
                content_type = 'application/octet-stream'
        else:
            mt = MimeType(mimestr=content_type)

        headers = [('Content-Type', content_type)]
        if content_length is not None:
            headers.append(('Content-Length', str(content_length)))
        if content_disposition is None and mt is not None:
            content_disposition = mt.content_disposition(app.cfg)
        if content_disposition:
            headers.append(('Content-Disposition', content_disposition))
        return headers


def cache_key(**kw):
    """
    Calculate a cache key (ascii only)

    Important key properties:

    * The key must be different for different <kw>.
    * Key is pure ascii

    :param kw: keys/values to compute cache key from
    """
    return hashlib.md5(repr(kw)).hexdigest()

