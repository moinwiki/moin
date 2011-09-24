# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - converter utilities
"""


from __future__ import absolute_import, division

from MoinMoin.util.mime import Type


def decode_data(data, contenttype=None):
    """
    read and decode data, return unicode text

    supported types for data:
    - rev object
    - str
    - unicode

    file-like objects and str need to be either utf-8 (or ascii, which is a subset of utf-8)
    encoded or contenttype (including a charset parameter) needs to be given.
    """
    if not isinstance(data, (str, unicode)):
        data = data.data.read()
    if isinstance(data, str):
        coding = 'utf-8'
        if contenttype is not None:
            ct = Type(contenttype)
            coding = ct.parameters.get('charset', coding)
        data = data.decode(coding)
    if not isinstance(data, unicode):
        raise TypeError("data must be rev or str (requires contenttype with charset) or unicode, but we got %r" % data)
    return data


def normalize_split_text(text):
    """
    normalize line endings, split text into a list of lines
    """
    text = text.replace(u'\r\n', u'\n')
    lines = text.split(u'\n')
    return lines

