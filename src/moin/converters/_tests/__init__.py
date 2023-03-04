import re
from io import StringIO
from xml.etree import ElementTree

from moin.utils.tree import moin_page, html, dc, mathml, svg, xinclude, xlink, docbook, xml


def serialize(elem, **options):
    with StringIO() as buffer:
        elem.write(buffer.write, **options)
        return buffer.getvalue()


# use non-greedy match for "..." part!
XMLNS_RE = re.compile(r'\s+xmlns(:\S+)?="[^"]+?"')
XMLNS_RE2 = re.compile(r'(\s+xmlns(:\w+)?="[^"]+?"|xmlns\(\w+=[^)]+?\)\s+)')
XMLNS_RE3 = re.compile(r'\s+xmlns="[^"]+?"')

TAGSTART_RE = re.compile(r'^(<[a-z:]+)')


def dump(el):
    """for use in debugging dump xml to stdout in a pretty format"""
    namespaces = {
        moin_page: 'moin_page',
        html: 'xhtml',
        dc: 'dc',
        mathml: 'mathml',
        svg: 'svg',
        xinclude: 'xinclude',
        xlink: 'xlink',
        docbook: 'docbook',
        xml: 'xml',
    }
    for ns, prefix in namespaces.items():
        ElementTree.register_namespace(prefix, str(ns))
    root = ElementTree.fromstring(serialize(el, namespaces=namespaces))
    ElementTree.indent(root, space='    ', level=0)
    ElementTree.dump(root)
