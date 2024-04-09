# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.smiley
"""

import pytest

from moin.converters.smiley import Converter, moin_page, ET
from . import serialize, XMLNS_RE3, TAGSTART_RE

etree = pytest.importorskip("lxml.etree")  # noqa


output_namespaces = {moin_page.namespace: ""}

input_re = TAGSTART_RE
output_re = XMLNS_RE3


def serialize_strip(elem, **options):
    result = serialize(elem, namespaces=output_namespaces, **options)
    return output_re.sub("", result)


@pytest.mark.parametrize(
    "input,query",
    [
        # normal
        (
            "<page><body><p>bla bla :-) bla bla</p></body></page>",
            '/page/body/p/span[@class="moin-text-icon moin-smile"]',
        ),
        # in code
        ("<page><body><code>bla bla :-) bla bla</code></body></page>", '/page/body[code="bla bla :-) bla bla"]'),
        # 2 at once
        (
            "<page><body><p>:-) :-(</p></body></page>",
            "/page/body/p"
            '[span[1][@class="moin-text-icon moin-smile"]]'
            '[span[2][@class="moin-text-icon moin-sad"]]',
        ),
        # strong
        (
            "<page><body><p><strong>:-)</strong></p></body></page>",
            '/page/body/p/strong/span[@class="moin-text-icon moin-smile"]',
        ),
        # Test to check we do not have bug with newline in the string
        ("<page><body><p>1\n2\n3\n4</p></body></page>", '/page/body[p="1\n2\n3\n4"]'),
        # Test with space between the elements
        ("<page><body><table-of-content />     <p>text</p></body></page>", '/page/body[p="text"]'),
        # Test the ignored tags
        ("<page><body><p><code>:-)</code></p></body></page>", '/page/body/p[code=":-)"]'),
        # Test the ignored tags and subelement
        (
            "<page><body><blockcode>:-)<strong>:-(</strong></blockcode></body></page>",
            '/page/body/blockcode[text()=":-)"][strong=":-("]',
        ),
    ],
)
def test_smiley_convert(input, query):
    conv = Converter()
    print("input:", input)
    out_elem = conv(ET.XML(input))
    after_conversion = serialize_strip(out_elem)
    print("output:", after_conversion)
    print("query:", query)
    tree = etree.fromstring(after_conversion)
    result = tree.xpath(query)
    print("query result:", result)
    assert result
