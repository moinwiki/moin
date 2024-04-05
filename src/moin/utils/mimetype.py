# Copyright: 2005-2011 MoinMoin:ThomasWaldmann
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - mimetype support
"""

import mimetypes

import pygments.lexers

from moin.constants.contenttypes import PARSER_TEXT_MIMETYPE

# prevents unexpected results on Windows
# see http://bugs.python.org/issue10551
mimetypes.init(mimetypes.knownfiles)

MIMETYPES_MORE = {
    # OpenOffice 2.x & other open document stuff
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".odg": "application/vnd.oasis.opendocument.graphics",
    ".odc": "application/vnd.oasis.opendocument.chart",
    ".odf": "application/vnd.oasis.opendocument.formula",
    ".odb": "application/vnd.oasis.opendocument.database",
    ".odi": "application/vnd.oasis.opendocument.image",
    ".odm": "application/vnd.oasis.opendocument.text-master",
    ".ott": "application/vnd.oasis.opendocument.text-template",
    ".ots": "application/vnd.oasis.opendocument.spreadsheet-template",
    ".otp": "application/vnd.oasis.opendocument.presentation-template",
    ".otg": "application/vnd.oasis.opendocument.graphics-template",
    # some systems (like Mac OS X) don't have some of these:
    ".patch": "text/x-diff",
    ".diff": "text/x-diff",
    ".py": "text/x-python",
    ".cfg": "text/plain",
    ".conf": "text/plain",
    ".irc": "text/plain",
    ".md5": "text/plain",
    ".csv": "text/csv",
    ".rst": "text/x-rst",
    ".flv": "video/x-flv",
    ".wmv": "video/x-ms-wmv",
    ".wma": "audio/x-ms-wma",
    ".swf": "application/x-shockwave-flash",
    ".swd": "application/x-svgdraw",
    ".dbx": "application/docbook+xml",
    ".moin": "text/x.moin.wiki",
    ".creole": "text/x.moin.creole",
    ".md": "text/x.markdown",
    ".markdown": "text/x.markdown",
    ".mediawiki": "text/x-mediawiki",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
    # supported compressed archives
    ".zip": "application/zip",
    ".tgz": "application/x-gtar",
    ".targz": "application/x-gtar",
}

# add all mimetype patterns of pygments
for name, short, patterns, mime in pygments.lexers.get_all_lexers():
    for pattern in patterns:
        if pattern.startswith("*.") and mime:
            if pattern in ("*.txt",):
                # there are some pygments lexers that claim *.txt for different
                # stuff than text/plain, we do not want that.
                continue
            MIMETYPES_MORE[pattern[1:]] = mime[0]

[mimetypes.add_type(mimetype, ext, True) for ext, mimetype in sorted(MIMETYPES_MORE.items())]

MIMETYPES_sanitize_mapping = {
    # this stuff is text, but got application/* for unknown reasons
    ("application", "docbook+xml"): ("text", "docbook"),
    ("application", "x-latex"): ("text", "latex"),
    ("application", "x-tex"): ("text", "tex"),
    ("application", "javascript"): ("text", "javascript"),
    ("application", "x-dos-batch"): ("text", "bat"),
}

MIMETYPES_spoil_mapping = {}  # inverse mapping of above
for _key, _value in MIMETYPES_sanitize_mapping.items():
    MIMETYPES_spoil_mapping[_value] = _key


class MimeType:
    """represents a mimetype like text/plain"""

    def __init__(self, mimestr=None, filename=None):
        self.major = self.minor = None  # sanitized mime type and subtype
        self.params = {}  # parameters like "charset" or others
        self.charset = None  # this stays None until we know for sure!
        self.raw_mimestr = mimestr
        self.filename = filename
        if mimestr:
            self.parse_mimetype(mimestr)
        elif filename:
            self.parse_filename(filename)

    def parse_filename(self, filename):
        mtype, encoding = mimetypes.guess_type(filename)
        if mtype is None:
            mtype = "application/octet-stream"
        self.parse_mimetype(mtype)

    def parse_mimetype(self, mimestr):
        """take a string like used in content-type and parse it into components,
        alternatively it also can process some abbreviated string like "wiki"
        """
        parameters = mimestr.split(";")
        parameters = [p.strip() for p in parameters]
        mimetype, parameters = parameters[0], parameters[1:]
        mimetype = mimetype.split("/")
        if len(mimetype) >= 2:
            major, minor = mimetype[:2]  # we just ignore more than 2 parts
        else:
            major, minor = self.parse_format(mimetype[0])
        self.major = major.lower()
        self.minor = minor.lower()
        for param in parameters:
            key, value = param.split("=")
            if value[0] == '"' and value[-1] == '"':  # remove quotes
                value = value[1:-1]
            self.params[key.lower()] = value
        if "charset" in self.params:
            self.charset = self.params["charset"].lower()
        self.sanitize()

    def parse_format(self, format):
        """maps from what we currently use on-page in a #format xxx processing
        instruction to a sanitized mimetype major, minor tuple.
        can also be user later for easier entry by the user, so he can just
        type "wiki" instead of "text/x.moin.wiki".
        """
        format = format.lower()
        if format in PARSER_TEXT_MIMETYPE:
            mimetype = "text", format
        else:
            mapping = {"wiki": ("text", "x.moin.wiki"), "irc": ("text", "irssi")}
            try:
                mimetype = mapping[format]
            except KeyError:
                mimetype = "text", f"x-{format}"
        return mimetype

    def sanitize(self):
        """convert to some representation that makes sense - this is not necessarily
        conformant to /etc/mime.types or IANA listing, but if something is
        readable text, we will return some ``text/*`` mimetype, not ``application/*``,
        because we need text/plain as fallback and not application/octet-stream.
        """
        self.major, self.minor = MIMETYPES_sanitize_mapping.get((self.major, self.minor), (self.major, self.minor))

    def spoil(self):
        """this returns something conformant to /etc/mime.type or IANA as a string,
        kind of inverse operation of sanitize(), but doesn't change self
        """
        major, minor = MIMETYPES_spoil_mapping.get((self.major, self.minor), (self.major, self.minor))
        return self.content_type(major, minor)

    def content_type(self, major=None, minor=None, charset=None, params=None):
        """return a string suitable for Content-Type header"""
        major = major or self.major
        minor = minor or self.minor
        params = params or self.params or {}
        if major == "text":
            charset = charset or self.charset
            if charset:
                params["charset"] = charset
        mimestr = f"{major}/{minor}"
        params = [f'{key.lower()}="{value}"' for key, value in params.items()]
        params.insert(0, mimestr)
        return ";".join(params)

    def mime_type(self):
        """return a string major/minor only, no params"""
        return f"{self.major}/{self.minor}"

    def as_attachment(self, cfg):
        # for dangerous files (like .html), when we are in danger of cross-site-scripting attacks,
        # we just let the user store them to disk ('attachment').
        # For safe files, we directly show them inline (this also works better for IE).
        mime_type = self.mime_type()
        return mime_type in cfg.mimetypes_xss_protect

    def module_name(self):
        """convert this mimetype to a string useable as python module name,
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
        fragments = modname.split("_")
        for length in range(len(fragments), 1, -1):
            yield "_".join(fragments[:length])
        yield self.raw_mimestr
        yield fragments[0]
        yield "application_octet_stream"
