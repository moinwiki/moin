# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Pygments driven syntax highlighting input converter
"""

try:
    import pygments
    import pygments.formatter
    import pygments.lexers
    from pygments.token import STANDARD_TYPES
except ImportError:
    pygments = None

from moin.utils.tree import moin_page
from ._util import decode_data, normalize_split_text

from moin import log

logging = log.getLogger(__name__)


if pygments:

    class TreeFormatter(pygments.formatter.Formatter):
        def _append(self, type, value, element):
            class_ = STANDARD_TYPES.get(type)
            if class_:
                value = moin_page.span(attrib={moin_page.class_: class_}, children=(value,))
            element.append(value)

        def format(self, tokensource, element):
            lastval = ""
            lasttype = None

            for ttype, value in tokensource:
                while ttype and ttype not in STANDARD_TYPES:
                    ttype = ttype.parent
                if ttype == lasttype:
                    lastval += value
                else:
                    if lastval:
                        self._append(lasttype, lastval, element)
                    lastval = value
                    lasttype = ttype

            if lastval:
                self._append(lasttype, lastval, element)

    class Converter:
        @classmethod
        def _factory(cls, type_input, type_output, **kw):
            pygments_name = None
            # first we check the input type against all mimetypes pygments knows:
            for name, short_names, patterns, mime_types in pygments.lexers.get_all_lexers():
                for mt in mime_types:
                    if Type(mt).issupertype(type_input):
                        pygments_name = name
                        break
                if pygments_name:
                    break

            # if we still don't know the lexer name for pygments, check some formats
            # that were supported by special parsers in moin 1.x:
            if pygments_name is None:
                moin_pygments = [
                    ("python", "Python"),
                    ("diff", "Diff"),
                    ("irssi", "IRC logs"),
                    ("irc", "IRC logs"),
                    ("java", "Java"),
                    ("cplusplus", "C++"),
                    ("pascal", "Delphi"),
                ]
                for moin_format, pygments_name in moin_pygments:
                    if Type(f"x-moin/format;name={moin_format}").issupertype(type_input):
                        break
                else:
                    pygments_name = None

            logging.debug("pygments_name: %r" % pygments_name)
            if pygments_name:
                lexer = pygments.lexers.find_lexer_class(pygments_name)
                return cls(lexer())

        def __init__(self, lexer=None, contenttype=None):
            """
            Create a Pygments Converter.

            :param lexer: pygments lexer instance
            :param contenttype: contenttype to get a lexer for
            """
            if lexer is None and contenttype is not None:
                ct = Type(contenttype)
                # pygments can't process parameters (like e.g. ...;charset=utf-8):
                mimetype = f"{ct.type}/{ct.subtype}"

                # TODO: fix pygments and remove this workaround for missing mimetypes; see issue #16
                alias_mimetypes = {
                    "text/x.moin.wiki": "text/x-trac-wiki",
                    "text/x.moin.creole": "text/x-trac-wiki",
                    "application/docbook+xml": "application/xml",
                }
                mimetype = alias_mimetypes[mimetype] if mimetype in alias_mimetypes else mimetype

                try:
                    lexer = pygments.lexers.get_lexer_for_mimetype(mimetype)
                except pygments.util.ClassNotFound:
                    lexer = pygments.lexers.get_lexer_for_mimetype("text/plain")
            self.lexer = lexer

        def __call__(self, data, contenttype=None, arguments=None):
            text = decode_data(data, contenttype)
            content = normalize_split_text(text)
            content = "\n".join(content)
            blockcode = moin_page.blockcode(attrib={moin_page.class_: "highlight"})
            pygments.highlight(content, self.lexer, TreeFormatter(), blockcode)
            body = moin_page.body(children=(blockcode,))
            return moin_page.page(children=(body,))

    from . import default_registry
    from moin.utils.mime import Type, type_moin_document

    default_registry.register(Converter._factory, Type(type="text"), type_moin_document)
    default_registry.register(Converter._factory, Type("x-moin/format"), type_moin_document)

else:
    # we have no Pygments, minimal Converter replacement, so highlight view does not crash
    class Converter:
        def __init__(self, lexer=None, contenttype=None):
            pass

        def __call__(self, content, arguments=None):
            """Parse the text and return DOM tree."""
            blockcode = moin_page.blockcode()
            for line in content:
                if len(blockcode):
                    blockcode.append("\n")
                blockcode.append(line.expandtabs())
            body = moin_page.body(children=(blockcode,))
            return moin_page.page(children=(body,))
