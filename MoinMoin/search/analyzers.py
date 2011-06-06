# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.analyzers Tokenizers and analyzers for indexing schema
"""


from flask import current_app as app
from whoosh.analysis import MultiFilter, IntraWordFilter, LowercaseFilter
from whoosh.analysis import Tokenizer, Token, RegexTokenizer

from MoinMoin.util.mime import Type
from MoinMoin.security import ContentACL


class MimeTokenizer(Tokenizer):
    def __call__(self, value):
        assert isinstance(value, unicode), "%r is not unicode" % value
        tk = Token()
        tp = Type(value)
        tk.text = tp.type
        yield tk
        tk.text = tp.subtype
        yield tk
        for key, value in tp.parameters.items():
            tk.text = u"%s=%s" % (key, value)
            yield tk


class AclTokenizer(Tokenizer):

    def __call__(self, value, **kwargs):
        assert isinstance(value, list) # so you'll notice if it blows up
        for acl_right in value:
            assert isinstance(acl_right, unicode), "%r is not unicode" % acl_right

        tk = Token()
        acl = ContentACL(app.cfg, value)
        for name, permissions in acl.acl:
            for permission in permissions:
                sign = "+" if permissions[permission] else "-"
                tk.text = u"%s:%s%s" % (name, sign, permission)
                yield tk


def item_name_analyzer(value, **kwargs):
    iwf = MultiFilter(index=IntraWordFilter(mergewords=True, mergenums=True),
                      query=IntraWordFilter(mergewords=False, mergenums=False)
                     )
    analyzer = RegexTokenizer(r"\S+") | iwf | LowercaseFilter()
    return analyzer
