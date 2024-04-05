# Copyright: 2000-2002 Juergen Hermann <jh@web.de>
# Copyright: 2006-2008 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:ReimarBauer
# Copyright: 2008-2010 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Moin Wiki 1.9 input converter
"""

import re

from moin import wikiutil
from moin.constants.misc import URI_SCHEMES
from moin.constants.chartypes import CHARS_LOWER, CHARS_UPPER
from moin.utils.interwiki import is_known_wiki
from moin.utils.iri import Iri
from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import moin_page, xlink

from . import default_registry
from .moinwiki_in import Converter

from moin import log

logging = log.getLogger(__name__)


class ConverterFormat19(Converter):
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    inline_freelink = r"""
         (?:
          (?<![%(u)s%(l)s/])  # require anything not upper/lower/slash before
          |
          ^  # ... or beginning of line
         )
         (?P<freelink_bang>\!)?  # configurable: avoid getting CamelCase rendered as link
         (?P<freelink>
          (?P<freelink_interwiki_ref>
           [A-Z][a-zA-Z]+
          )
          \:
          (?P<freelink_interwiki_page>
           (?=\S*[%(u)s%(l)s0..9]\S* )  # make sure there is something non-blank with at >= 1 alphanum letter following
           [^\s"\'}\]|:,.\)?!]+  # we take all until we hit some blank or punctuation char ...
          )
          |
          (?P<freelink_page>
           (?:
            (%(parent)s)*  # there might be either ../ parent prefix(es)
            |
            ((?<!%(child)s)%(child)s)?  # or maybe a single / child prefix (but not if we already had it before)
           )
           (
            ((?<!%(child)s)%(child)s)?  # there might be / child prefix (but not if we already had it before)
            (?:[%(u)s][%(l)s]+){2,}  # at least 2 upper>lower transitions make CamelCase
           )+  # we can have MainPage/SubPage/SubSubPage ...
           (?:
            \#  # anchor separator          TODO check if this does not make trouble at places where word_rule is used
            \S+  # some anchor name
           )?
          )
          |
          (?P<freelink_email>
           [-\w._+]+  # name
           \@  # at
           [\w-]+(\.[\w-]+)+  # server/domain
          )
         )
         (?:
          (?![%(u)s%(l)s/])  # require anything not upper/lower/slash following
          |
          $  # ... or end of line
         )
    """ % {
        "u": CHARS_UPPER,
        "l": CHARS_LOWER,
        "child": re.escape(wikiutil.CHILD_PREFIX),
        "parent": re.escape(wikiutil.PARENT_PREFIX),
    }

    def inline_freelink_repl(
        self,
        stack,
        freelink,
        freelink_bang=None,
        freelink_interwiki_page=None,
        freelink_interwiki_ref=None,
        freelink_page=None,
        freelink_email=None,
    ):
        if freelink_bang:
            stack.top_append(freelink)
            return

        attrib = {}

        if freelink_page:
            if "#" in freelink_page:
                path, fragment = freelink_page.rsplit("#", 1)
            else:
                path, fragment = freelink_page, None
            link = Iri(scheme="wiki.local", path=path, fragment=fragment)
            text = freelink_page

        elif freelink_email:
            link = "mailto:" + freelink_email
            text = freelink_email

        else:
            if not is_known_wiki(freelink_interwiki_ref):
                stack.top_append(freelink)
                return

            link = Iri(scheme="wiki", authority=freelink_interwiki_ref, path="/" + freelink_interwiki_page)
            text = freelink_interwiki_page

        attrib[xlink.href] = link

        element = moin_page.a(attrib, children=[text])
        stack.top_append(element)

    inline_url = r"""
        (?P<url>
            (
                ^
                |
                (?<=
                    \s
                    |
                    [.,:;!?()/=]
                )
            )
            (?P<url_target>
                (%(uri_schemes)s):
                \S+?
            )
            (
                $
                |
                (?=
                    \s
                    |
                    [,.:;!?()]
                    (\s | $)
                )
            )
        )
    """ % dict(
        uri_schemes="|".join(URI_SCHEMES)
    )

    def inline_url_repl(self, stack, url, url_target):
        url = Iri(url_target)
        attrib = {xlink.href: url}
        element = moin_page.a(attrib=attrib, children=[url_target])
        stack.top_append(element)

    inline = Converter.inline + (inline_freelink, inline_url)
    inline_re = re.compile("|".join(inline), re.X | re.U)


default_registry.register(ConverterFormat19.factory, Type("text/x.moin.wiki;format=1.9"), type_moin_document)
default_registry.register(ConverterFormat19.factory, Type("x-moin/format;name=wiki;format=1.9"), type_moin_document)
