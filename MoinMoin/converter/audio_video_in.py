"""
MoinMoin - Audio/Video converter

Convert audio/video to <object> tag for the DOM Tree.

Note: currently this is quite same as image_in.

@copyright: 2010 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import moin_page, xlink

class Converter(object):
    """
    Convert audio/video to the corresponding <object> in the DOM Tree
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls(input_type=input)

    def __init__(self, input_type):
        self.input_type = input_type

    def __call__(self, content):
        item_name = content # we just give the name of the item in the content
        attrib = {
            moin_page.type_: unicode(self.input_type),
            xlink.href: Iri(scheme='wiki', authority='', path='/'+item_name, query='do=get'),
        }
        return moin_page.object_(attrib=attrib, children=[u'Your Browser does not support HTML5 audio/video element.', ])


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('video/ogg'), type_moin_document)
default_registry.register(Converter._factory, Type('video/webm'), type_moin_document)
default_registry.register(Converter._factory, Type('audio/ogg'), type_moin_document)
default_registry.register(Converter._factory, Type('audio/wave'), type_moin_document)

