# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.analyzers Tokenizers and analyzers for indexing schema
"""

from re import split

from flask import current_app as app
from whoosh.analysis import MultiFilter, IntraWordFilter, LowercaseFilter
from whoosh.analysis import Tokenizer, Token, RegexTokenizer

from MoinMoin.util.mime import Type
from MoinMoin.security import ContentACL


class MimeTokenizer(Tokenizer):
    """ Content type tokenizer """

    def __call__(self, value, start_pos=0, positions=False, **kwargs):
        """
        Calls tokenizer

        Tokenizer behaviour:

        Input: text/x.moin.wiki;charset=utf-8
        Output: "text", "x.moin.wiki", "charset=utf-8"

        Input: application/pdf
        Output: "application", "pdf"

        :param value: String for tokenization
        :param start_pos: The position number of the first token. For example,
            if you set start_pos=2, the tokens will be numbered 2,3,4,...
            instead of 0,1,2,...
        :param positions: Whether to record token positions in the token.
        """

        assert isinstance(value, unicode), "%r is not unicode" % value
        if u'/' not in value: # Add '/' if user forgot do this
            value += u'/'
        pos = start_pos
        tk = Token()
        tp = Type(value)
        tk.text = tp.type
        if positions:
            tk.pos = pos
            pos += 1
        yield tk
        if tp.subtype is not None:
            tk.text = tp.subtype
            if positions:
                tk.pos = pos
                pos += 1
            yield tk
        for key, value in tp.parameters.items():
            tk.text = u"%s=%s" % (key, value)
            if positions:
                tk.pos = pos
                pos += 1
            yield tk


class AclTokenizer(Tokenizer):
    """ Access control list tokenizer """

    def __call__(self, value, start_pos=0, positions=False, **kwargs):
        """
        Calls tokenizer

        Input: u"JoeDoe,JaneDoe:admin,read,write,destroy +EditorGroup:write All:read"

        Output: "JoeDoe", "JoeDoe:admin", "JoeDoe:read", "JoeDoe:write", "JoeDoe:destroy",
            (... equivalent tokens for JaneDoe ...),
            "EditorGroup", "EditorGroup:write",
            "All", "All:read"

        :param value: String for tokenization
        :param start_pos: The position number of the first token. For example,
            if you set start_pos=2, the tokens will be numbered 2,3,4,...
            instead of 0,1,2,...
        :param positions: Whether to record token positions in the token.
        """

        assert isinstance(value, unicode) # so you'll notice if it blows up
        pos = start_pos
        tk = Token()
        acl = ContentACL(app.cfg, [value])
        for name, permissions in acl.acl:
            for permission in permissions:
                sign = "+" if permissions[permission] else "-"
                tk.text = u"%s:%s%s" % (name, sign, permission)
                if positions:
                    tk.pos = pos
                    pos += 1
                yield tk

def item_name_analyzer():
    """ 
    Calls tokenizer

    Input: "some item name", "SomeItem/SubItem", "GSOC2011"

    Output: "some", "item", "name"; "Some", "Item", "Sub", "Item"; "GSOC", "2011";
    """
    iwf = MultiFilter(index=IntraWordFilter(mergewords=True, mergenums=True),
                      query=IntraWordFilter(mergewords=False, mergenums=False)
                     )
    analyzer = RegexTokenizer(r"\S+") | iwf | LowercaseFilter()
    return analyzer
