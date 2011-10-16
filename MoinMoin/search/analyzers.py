# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Misc. tokenizers and analyzers for whoosh indexing
"""

from whoosh.analysis import MultiFilter, IntraWordFilter, LowercaseFilter
from whoosh.analysis import Tokenizer, Token, RegexTokenizer

from MoinMoin.util.mime import Type
from MoinMoin.security import AccessControlList


class MimeTokenizer(Tokenizer):
    """ Content type tokenizer """

    def __call__(self, value, start_pos=0, positions=False, **kwargs):
        """
        Tokenizer behaviour:

        Input: u"text/x.moin.wiki;charset=utf-8"
        Output: u"text/x.moin.wiki;charset=utf-8", u"text", u"x.moin.wiki", u"charset=utf-8"

        Input: u"application/pdf"
        Output: u"application/pdf", u"application", u"pdf"

        :param value: String for tokenization
        :param start_pos: The position number of the first token. For example,
            if you set start_pos=2, the tokens will be numbered 2,3,4,...
            instead of 0,1,2,...
        :param positions: Whether to record token positions in the token.
        """
        assert isinstance(value, unicode), "{0!r} is not unicode".format(value)
        if u'/' not in value: # Add '/' if user forgot do this
            value += u'/'
        pos = start_pos
        tk = Token()
        tp = Type(value)
        # we need to yield the complete contenttype in one piece,
        # so we can find it with Term(CONTENTTYPE, contenttype):
        if tp.type is not None and tp.subtype is not None:
            # note: we do not use "value" directly, so Type.__unicode__ can normalize it:
            tk.text = unicode(tp)
            if positions:
                tk.pos = pos
                pos += 1
            yield tk
        # now yield the pieces:
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
            tk.text = u"{0}={1}".format(key, value)
            if positions:
                tk.pos = pos
                pos += 1
            yield tk


class AclTokenizer(Tokenizer):
    """ Access control list tokenizer """

    def __init__(self, acl_rights_contents):
        """
        :param cfg: wiki config
        """
        self._acl_rights_contents = acl_rights_contents

    def __call__(self, value, start_pos=0, positions=False, mode=u'', **kwargs):
        """
        Calls AccessControlList for tokenization

        Analyzer behaviour:

        In index mode:
            Input: u"JoeDoe,JaneDoe:admin,read,write,destroy +EditorGroup:write All:read"

            Output: "u'JoeDoe:+read', u'JoeDoe:+write', u'JoeDoe:-create', u'JoeDoe:+admin',
                     u'JoeDoe:+destroy', u'JaneDoe:+read', u'JaneDoe:+write', u'JaneDoe:-create',
                     u'JaneDoe:+admin', u'JaneDoe:+destroy', u'EditorGroup:+write', u'All:+read',
                     u'All:-write', u'All:-create', u'All:-admin', u'All:-destroy'

        In query mode:
            Input: u"JoeDoe:+write"

            Output: u"JoeDoe:+write"

        :param value: unicode string
        :param positions: Whether to record token positions in the token.
        :param start_pos: The position number of the first token. For example,
            if you set start_pos=2, the tokens will be numbered 2,3,4,...
            instead of 0,1,2,...
        """
        assert isinstance(value, unicode)
        pos = start_pos
        tk = Token()
        tk.mode = mode
        if mode == "query":
            tk.text = value
            if positions:
                tk.pos = pos
            yield tk
        else:
            acl = AccessControlList([value], valid=self._acl_rights_contents)
            for name, permissions in acl.acl:
                for permission in permissions:
                    sign = "+" if permissions[permission] else "-"
                    tk.text = u"{0}:{1}{2}".format(name, sign, permission)
                    if positions:
                        tk.pos = pos
                        pos += 1
                    yield tk


def item_name_analyzer():
    """
    Analyzer behaviour:

    Input: u"some item name", u"SomeItem/SubItem", u"GSOC2011"

    Output: u"some", u"item", u"name"; u"Some", u"Item", u"Sub", u"Item"; u"GSOC", u"2011"
    """
    iwf = MultiFilter(index=IntraWordFilter(mergewords=True, mergenums=True),
                      query=IntraWordFilter(mergewords=False, mergenums=False)
                     )
    analyzer = RegexTokenizer(r"\S+") | iwf | LowercaseFilter()
    return analyzer

