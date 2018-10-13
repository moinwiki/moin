# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converter.default_registry
"""

import pytest

from moin.utils.mime import Type, type_moin_document, type_moin_wiki
from moin.converter import default_registry
from moin.converter.text_in import Converter as TextInConverter
from moin.converter.moinwiki_in import Converter as MoinwikiInConverter
from moin.converter.html_in import Converter as HtmlInConverter
from moin.converter.pygments_in import Converter as PygmentsInConverter
from moin.converter.everything import Converter as EverythingConverter

from moin.converter.html_out import ConverterPage as HtmlOutConverterPage
from moin.converter.moinwiki_out import Converter as MoinwikiOutConverter

from moin.converter.macro import Converter as MacroConverter
from moin.converter.include import Converter as IncludeConverter
from moin.converter.link import ConverterExternOutput as LinkConverterExternOutput
from moin.converter.link import ConverterItemRefs as LinkConverterItemRefs


@pytest.mark.parametrize('type_input,type_output,expected_class', [
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
])
def test_converter_finder(type_input, type_output, expected_class):
    conv = default_registry.get(type_input, type_output)
    assert isinstance(conv, expected_class)


@pytest.mark.parametrize('kwargs,expected_class', [
    # DOM converters, which depend on keyword argument to default_registry.get
    (dict(macros='expandall'), MacroConverter),
    (dict(includes='expandall'), IncludeConverter),
    (dict(links='extern'), LinkConverterExternOutput),
    (dict(items='refs'), LinkConverterItemRefs),
])
def test_converter_args(kwargs, expected_class):
    conv = default_registry.get(type_moin_document, type_moin_document, **kwargs)
    assert isinstance(conv, expected_class)


coverage_modules = ['moin.converter']
