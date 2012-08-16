# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.default_registry
"""


import pytest

from MoinMoin.util.mime import Type, type_moin_document, type_moin_wiki
from MoinMoin.converter import default_registry
from MoinMoin.converter.text_in import Converter as TextInConverter
from MoinMoin.converter.moinwiki_in import Converter as MoinwikiInConverter
from MoinMoin.converter.html_in import Converter as HtmlInConverter
from MoinMoin.converter.pygments_in import Converter as PygmentsInConverter
from MoinMoin.converter.everything import Converter as EverythingConverter

from MoinMoin.converter.html_out import ConverterPage as HtmlOutConverterPage
from MoinMoin.converter.moinwiki_out import Converter as MoinwikiOutConverter

from MoinMoin.converter.highlight import Converter as HighlightConverter
from MoinMoin.converter.macro import Converter as MacroConverter
from MoinMoin.converter.include import Converter as IncludeConverter
from MoinMoin.converter.link import ConverterExternOutput as LinkConverterExternOutput
from MoinMoin.converter.link import ConverterItemRefs as LinkConverterItemRefs


class TestRegistry(object):
    def testConverterFinder(self):
        for type_input, type_output, ExpectedClass in [
                # *_in converters
                (type_moin_wiki, type_moin_document, MoinwikiInConverter),
                (Type('x-moin/format;name=wiki'), type_moin_document, MoinwikiInConverter),
                # pygments_in can handle this too but html_in should have more priority
                (Type('text/html'), type_moin_document, HtmlInConverter),
                # fall back to pygments_in
                (Type('text/html+jinja'), type_moin_document, PygmentsInConverter),
                # fallback for any random text/* input types
                (Type('text/blahblah'), type_moin_document, TextInConverter),
                # fallback for anything
                (Type('mua/haha'), type_moin_document, EverythingConverter),

                # *_out converters
                (type_moin_document, Type('application/x-xhtml-moin-page'), HtmlOutConverterPage),
                (type_moin_document, type_moin_wiki, MoinwikiOutConverter),
                (type_moin_document, Type('x-moin/format;name=wiki'), MoinwikiOutConverter),
            ]:
            conv = default_registry.get(type_input, type_output)
            assert isinstance(conv, ExpectedClass)

        for kwargs, ExpectedClass in [
                # DOM converters, which depend on keyword argument to default_registry.get
                (dict(macros='expandall'), MacroConverter),
                (dict(includes='expandall'), IncludeConverter),
                (dict(links='extern'), LinkConverterExternOutput),
                (dict(items='refs'), LinkConverterItemRefs),
            ]:
            conv = default_registry.get(type_moin_document, type_moin_document, **kwargs)
            assert isinstance(conv, ExpectedClass)


coverage_modules = ['MoinMoin.converter']
