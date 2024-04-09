# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - converter utilities
"""

try:
    from flask import g as flaskg
except ImportError:
    # in case converters become an independent package
    flaskg = None
from emeraldtree import ElementTree as ET

from moin.constants.misc import URI_SCHEMES
from moin.utils.iri import Iri
from moin.utils.mime import Type
from moin.utils.tree import html, moin_page


def allowed_uri_scheme(uri):
    parsed = Iri(uri)
    return not parsed.scheme or parsed.scheme in URI_SCHEMES


def decode_data(data, contenttype=None):
    """
    read and decode data, return unicode text

    supported types for data:
    - rev object
    - bytes
    - str

    file-like objects and bytes need to be either utf-8 (or ascii, which is a subset of utf-8)
    encoded or contenttype (including a charset parameter) needs to be given.
    """
    if not isinstance(data, (bytes, str)):
        data = data.data.read()
    if isinstance(data, bytes):
        coding = "utf-8"
        if contenttype is not None:
            ct = Type(contenttype)
            coding = ct.parameters.get("charset", coding)
        data = data.decode(coding)
    if not isinstance(data, str):
        raise TypeError(
            "data must be rev or bytes (requires contenttype with charset) or str, " "but we got {!r}".format(data)
        )
    return data


def normalize_split_text(text):
    """
    normalize line endings, split text into a list of lines
    """
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    return lines


class _Iter:
    """
    Iterator with push back support

    Collected items can be pushed back into the iterator and further calls will
    return them.

    Increments a counter tracking the current line number. This is used by _Stack to
    add an attribute used by javascript to autoscroll the edit textarea.
    """

    def __init__(self, parent, startno=0):
        self.__finished = False
        self.__parent = iter(parent)
        self.__prepend = []
        self.lineno = startno

    def __iter__(self):
        return self

    def __next__(self):
        if self.__finished:
            raise StopIteration

        self.lineno += 1
        if self.__prepend:
            return self.__prepend.pop(0)

        try:
            return next(self.__parent)
        except StopIteration:
            self.__finished = True
            raise

    def push(self, item):
        self.__prepend.append(item)
        self.lineno -= 1


class _Stack:
    class Item:
        def __init__(self, elem):
            self.elem = elem
            if elem.tag.uri == moin_page:
                self.name = elem.tag.name
            else:
                self.name = None

    def __init__(self, bottom=None, iter_content=None):
        self._list = []
        if bottom:
            self._list.append(self.Item(bottom))
        self.iter_content = iter_content
        self.last_lineno = 0

    def __len__(self):
        return len(self._list)

    def add_lineno(self, elem):
        """
        Add a custom attribute (data-lineno=nn) that will be used by Javascript to scroll edit textarea.
        """
        if flaskg and getattr(flaskg, "add_lineno_attr", False):
            if self.last_lineno != self.iter_content.lineno:
                # avoid adding same lineno to parent and multiple children or grand-children
                elem.attrib[html.data_lineno] = self.iter_content.lineno
                self.last_lineno = self.iter_content.lineno

    def clear(self):
        del self._list[1:]

    def pop(self):
        self._list.pop()

    def pop_name(self, *names):
        """
        Remove anything from the stack including the given node.
        """
        while len(self._list) > 2 and not self.top_check(*names):
            self.pop()
        self.pop()

    def push(self, elem):
        self.top_append(elem)
        self._list.append(self.Item(elem))

    def top(self):
        return self._list[-1].elem

    def top_append(self, elem):
        if isinstance(elem, ET.Node):
            self.add_lineno(elem)
        self.top().append(elem)

    def top_append_ifnotempty(self, elem):
        if elem:
            self.top_append(elem)

    def top_check(self, *names, **kwargs):
        """
        Check if the top of the stack name and attrib matches the parameters.
        """
        attrib = kwargs.get("attrib", {})
        return self._list[-1].name in names and set(attrib.items()).issubset(set(self._list[-1].elem.attrib.items()))
