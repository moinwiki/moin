"""
MoinMoin - Simple text input converter.

It just puts all text into a code block. It acts as a wildcard for text/* input.

We keep it at MIDDLE+2 prio in the registry, one after pygments converter, so
it is a fallback for the case we have no pygments or pygments has no support
for the input mimetype.

@copyright: 2008 MoinMoin:ThomasWaldmann,
            2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin.util.tree import moin_page

class Converter(object):
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """
    @classmethod
    def _factory(cls, type_input, type_output, **kw):
        return cls()

    def __call__(self, content, arguments=None):
        """Parse the text and return DOM tree."""
        blockcode = moin_page.blockcode()
        for line in content:
            if len(blockcode):
                blockcode.append('\n')
            blockcode.append(line.expandtabs())
        body = moin_page.body(children=(blockcode, ))
        return moin_page.page(children=(body, ))


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type(type='text'), type_moin_document,
                          default_registry.PRIORITY_MIDDLE + 2)

