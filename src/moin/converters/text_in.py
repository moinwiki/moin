# Copyright: 2008 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Simple text input converter.

It just puts all text into a code block. It acts as a wildcard for text/* input.

We keep it at MIDDLE+2 prio in the registry, one after pygments converter, so
it is a fallback for the case we have no pygments or pygments has no support
for the input mimetype.
"""

from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import moin_page

from . import default_registry
from ._util import decode_data, normalize_split_text


class Converter:
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """

    @classmethod
    def _factory(cls, type_input, type_output, **kw):
        return cls()

    def __call__(self, data, contenttype=None, arguments=None):
        text = decode_data(data, contenttype)
        content = normalize_split_text(text)
        blockcode = moin_page.blockcode()
        for line in content:
            if len(blockcode):
                blockcode.append("\n")
            blockcode.append(line.expandtabs())
        body = moin_page.body(children=(blockcode,))
        return moin_page.page(children=(body,))


# Assign a lower priority (= bigger number) so that it is tried after pygments_in
default_registry.register(
    Converter._factory, Type(type="text"), type_moin_document, default_registry.PRIORITY_MIDDLE + 1
)
