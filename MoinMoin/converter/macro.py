# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Macro handling

Expands all macro elements in an internal Moin document.
"""


from __future__ import absolute_import, division

from flask import current_app as app

from emeraldtree import ElementTree as ET

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.util import plugins
from MoinMoin.i18n import _, L_, N_
from MoinMoin.converter._args import Arguments
from MoinMoin.util import iri
from MoinMoin.util.mime import type_moin_document, Type
from MoinMoin.util.tree import html, moin_page
from MoinMoin.util.plugins import PluginMissingError


class Converter(object):
    @classmethod
    def _factory(cls, input, output, macros=None, **kw):
        if macros == 'expandall':
            return cls()

    def handle_macro(self, elem, page):
        logging.debug("handle_macro elem: %r" % elem)
        type = elem.get(moin_page.content_type)
        alt = elem.get(moin_page.alt)

        if not type:
            return

        type = Type(type)
        if not (type.type == 'x-moin' and type.subtype == 'macro'):
            logging.debug("not a macro, skipping: %r" % type)
            return

        name = type.parameters['name']

        context_block = elem.tag == moin_page.part

        args_tree = None
        for item in elem:
            if item.tag.uri == moin_page.namespace:
                if item.tag.name in ('body', 'inline-body'):
                    return
                if item.tag.name == 'arguments':
                    args_tree = item

        args = None
        if args_tree:
            args = Arguments()
            for arg in args_tree:
                key = arg.get(moin_page.name)
                value = arg[0]
                if key:
                    args.keyword[key] = value
                else:
                    args.positional.append(value)

        elem_body = context_block and moin_page.body() or moin_page.inline_body()
        elem_error = moin_page.error()

        try:
            cls = plugins.importPlugin(app.cfg, 'macro', name, function='Macro')
            macro = cls()
            ret = macro((), args, page, alt, context_block)
            elem_body.append(ret)

        except PluginMissingError:
            elem_error.append('<<%s>> %s' % (name, _('Error: invalid macro name.')))

        except Exception as e:
            # we do not want that a faulty macro aborts rendering of the page
            # and makes the wiki UI unusable (by emitting a Server Error),
            # thus, in case of exceptions, we just log the problem and return
            # some standard text.
            logging.exception("Macro {0} raised an exception:".format(name))
            elem_error.append(_('<<%(macro_name)s: execution failed [%(error_msg)s] (see also the log)>>',
                    macro_name=name,
                    error_msg=unicode(e),
                ))

        if len(elem_body):
            elem.append(elem_body)
        if len(elem_error):
            elem.append(elem_error)

    def recurse(self, elem, page):
        new_page_href = elem.get(moin_page.page_href)
        if new_page_href:
            page = iri.Iri(new_page_href)

        if elem.tag in (moin_page.part, moin_page.inline_part):
            yield elem, page

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page):
                    yield i

    def __call__(self, tree):
        for elem, page in self.recurse(tree, None):
            self.handle_macro(elem, page)
        return tree

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, type_moin_document, type_moin_document)
