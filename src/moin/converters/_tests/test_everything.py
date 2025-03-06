# Copyright: 2025 MoinMoin
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.everything
"""

import pytest

from . import serialize, XMLNS_RE

from moin.constants.keys import CONTENTTYPE, ITEMTYPE, REV_NUMBER
from moin.converters.everything import Converter
from moin.items.content import Content

from moin.utils.interwiki import split_fqname

from moin.items import Item
from moin.utils.tree import moin_page, xlink, html, xinclude

from unittest.mock import Mock

namespaces = {moin_page: "", xlink: "xlink", html: "xhtml", xinclude: "xinclude"}

meta = {CONTENTTYPE: "binary/blob", ITEMTYPE: "default", REV_NUMBER: 1}

output_re = XMLNS_RE


def serialize_strip(elem, **options):
    result = serialize(elem, namespaces=namespaces, **options)
    return output_re.sub("", result)


@pytest.mark.parametrize(
    "input,output",
    [
        (
            "machines/nuc/fw2.blob",
            '<page><body><a xlink:href="wiki:///machines/nuc/fw2.blob?do=get&amp;rev=691da3aa1dd146d296bcd9ac92b25be5">Download machines/nuc/fw2.blob.</a></body></page>',
        )
    ],
)
def test_conv(input, output):
    rev = Mock()
    rev.meta = meta
    rev.revid = "691da3aa1dd146d296bcd9ac92b25be5"
    rev.item = Item(split_fqname(input), rev=rev, content=Content.create(meta[CONTENTTYPE]))
    conv = Converter()
    out = conv(rev, rev.item.contenttype)
    assert serialize_strip(out) == output
