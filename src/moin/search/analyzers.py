# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Misc. tokenizers and analyzers for whoosh indexing
"""

from whoosh.analysis import MultiFilter, IntraWordFilter, LowercaseFilter
from whoosh.analysis import Tokenizer, Token, RegexTokenizer

from moin.security import AccessControlList


class MimeTokenizer(Tokenizer):
    """Content type tokenizer"""

    def __call__(self, value, start_pos=0, positions=False, mode="", **kwargs):
        """
        This tokenizer is used for both indexing and queries. Queries are simple, usually return the input value as is.

        For indexing, tokens are generated for the incoming value plus various parts as shown below. Special cases
        create tokens for moinwiki, jpg, and mp3.

        Input: "text/x.moin.wiki;charset=utf-8"
        Output: "text/x.moin.wiki;charset=utf-8", "text", "moinwiki", "x.moin.wiki", "x", "moin",
                "wiki", "charset=utf-8", "charset", "utf-8"

        Input: "application/pdf"
        Output: "application/pdf", "application", "pdf"

        :param value: String for tokenization
        :mode value: query or index
        :param start_pos: The position number of the first token. For example,
            if you set start_pos=2, the tokens will be numbered 2,3,4,...
            instead of 0,1,2,...
        :param positions: Whether to record token positions in the token. These are unwanted,
            but positions=True is passed on indexing, positions=False on queries.
        """
        tk = Token()
        tk.pos = 0
        if mode == "query":
            # 1 term expected, but contenttype:'moin utf-8' is valid
            val = value.split()
            for v in val:
                tk.text = v
                yield tk
        else:
            # mode = 'index'
            tk.text = value
            # text/x.moin.wiki;charset=utf-8
            yield tk
            if "/" not in value:
                # unsupported contenttype
                return
            major, minor = value.split("/")
            # text, x.moin.wiki;charset=utf-8
            tk.text = major
            # text
            yield tk
            if ";" in minor:
                parameters = minor.split(";")
                # x.moin.wiki, charset=utf-8
                for par in parameters[1:]:
                    tk.text = par
                    # charset=utf-8
                    yield tk
                    key, val = par.split("=")
                    # charset, utf-8
                    tk.text = key
                    # charset
                    yield tk
                    tk.text = val
                    # utf-8
                    yield tk
                minor = parameters[0]  # x.moin.wiki
            if minor == "mpeg":
                # 'audio/mpeg' most people expect mp3
                tk.text = "mp3"
                yield tk
            if minor == "jpeg":
                # 'image/jpeg' most people expect jpg
                tk.text = "jpg"
                yield tk
            if minor == "x.moin.wiki":
                # moin is valid for moin and creole, use this to get just moin
                tk.text = "moinwiki"
                yield tk
            tk.text = minor
            # x.moin.wiki
            yield tk
            if "." in minor:
                min = minor.split(".")
                # x, moin, wiki
                for m in min:
                    tk.text = m
                    yield tk
            if "-" in minor:
                # x-markdown
                min = minor.split("-")
                for m in min:
                    tk.text = m
                    yield tk
            if "+" in minor:
                # svg+xml
                min = minor.split("+")
                for m in min:
                    tk.text = m
                    yield tk


class AclTokenizer(Tokenizer):
    """Access control list tokenizer"""

    def __init__(self, acl_rights_contents):
        """
        :param acl_rights_contents: ACL for contents
        """
        self._acl_rights_contents = acl_rights_contents

    def __call__(self, value, start_pos=0, positions=False, mode="", **kwargs):
        """
        Calls AccessControlList for tokenization

        Analyzer behaviour:

        In index mode:
            Input: "JoeDoe,JaneDoe:admin,read,write,destroy +EditorGroup:write All:read"

            Output: "'JoeDoe:+read', 'JoeDoe:+write', 'JoeDoe:-create', 'JoeDoe:+admin',
                     'JoeDoe:+destroy', 'JaneDoe:+read', 'JaneDoe:+write', 'JaneDoe:-create',
                     'JaneDoe:+admin', 'JaneDoe:+destroy', 'EditorGroup:+write', 'All:+read',
                     'All:-write', 'All:-create', 'All:-admin', 'All:-destroy'

        In query mode:
            Input: "JoeDoe:+write"

            Output: "JoeDoe:+write"

        :param value: str
        :param positions: Whether to record token positions in the token.
        :param start_pos: The position number of the first token. For example,
            if you set start_pos=2, the tokens will be numbered 2,3,4,...
            instead of 0,1,2,...
        """
        assert isinstance(value, str)
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
                    tk.text = f"{name}:{sign}{permission}"
                    if positions:
                        tk.pos = pos
                        pos += 1
                    yield tk


def item_name_analyzer():
    """
    Analyzer behaviour:

    Input: "some item name", "SomeItem/SubItem", "GSOC2011"

    Output: "some", "item", "name"; "Some", "Item", "Sub", "Item"; "GSOC", "2011"
    """
    iwf = MultiFilter(
        index=IntraWordFilter(mergewords=True, mergenums=True), query=IntraWordFilter(mergewords=False, mergenums=False)
    )
    analyzer = RegexTokenizer(r"\S+") | iwf | LowercaseFilter()
    return analyzer
