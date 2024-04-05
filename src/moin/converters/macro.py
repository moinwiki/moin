# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Macro handling

Expands all macro elements in an internal Moin document.
"""

from flask import current_app as app

from emeraldtree import ElementTree as ET

from moin.utils import plugins
from moin.i18n import _
from moin.utils import iri
from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import moin_page
from moin.utils.plugins import PluginMissingError

from . import default_registry

from moin import log

logging = log.getLogger(__name__)


class Converter:
    @classmethod
    def _factory(cls, input, output, macros=None, **kw):
        if macros == "expandall":
            return cls()

    def handle_macro(self, elem, page):
        logging.debug(f"handle_macro elem: {elem!r}")
        type = elem.get(moin_page.content_type)
        alt = elem.get(moin_page.alt)

        if not type:
            return

        type = Type(type)
        if not (type.type == "x-moin" and type.subtype == "macro"):
            logging.debug(f"not a macro, skipping: {type!r}")
            return

        name = type.parameters["name"]
        context_block = elem.tag == moin_page.part
        args = elem[0] if len(elem) else None
        elem_body = context_block and moin_page.body() or moin_page.inline_body()
        elem_error = moin_page.error()

        try:
            cls = plugins.importPlugin(app.cfg, "macros", name, function="Macro")
            macro = cls()
            ret = macro((), args, page, alt, context_block)
            elem_body.append(ret)

        except PluginMissingError:
            elem_error.append(f"<<{name}>> {_('Error: invalid macro name.')}")

        except Exception as e:
            # we do not want that a faulty macro aborts rendering of the page
            # and makes the wiki UI unusable (by emitting a Server Error),
            # thus, in case of exceptions, we just log the problem and return
            # some standard text.
            logging.exception(f"Macro {name} raised an exception:")
            elem_error.append(
                _("<<{macro_name}: execution failed [{error_msg}] (see also the log)>>").format(
                    macro_name=name, error_msg=str(e)
                )
            )

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
                yield from self.recurse(child, page)

    def __call__(self, tree):
        for elem, page in self.recurse(tree, None):
            self.handle_macro(elem, page)
        return tree


default_registry.register(Converter._factory, type_moin_document, type_moin_document)
