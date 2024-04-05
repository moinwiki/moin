# Copyright: 2008,2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Generic? IRI implementation

Implements the generic IRI form as defined in RFC 3987.
"""


import codecs
import re
from moin.utils.pysupport import AutoNe


def _iriquote_replace(exc):
    """
    Special replace function that implements the IRI quoting rules
    """
    if not isinstance(exc, UnicodeDecodeError):
        raise exc

    text = "".join("%%%02X" % code for code in exc.object[exc.start : exc.end])
    return text, exc.end


codecs.register_error("iriquote", _iriquote_replace)


class Iri(AutoNe):
    __slots__ = "_scheme", "_authority", "_path", "_query", "_fragment"

    overall_rules = r"""
    ^
    (
        (?P<scheme>
            [^:/?\#]+
        )
        :
    )?
    (
        //
        (?P<authority>
            [^/?\#]*
        )
    )?
    (?P<path>
        [^?\#]+
    )?
    (
        \?
        (?P<query>
            [^\#]*
        )
    )?
    (
        \#
        (?P<fragment>
            .*
        )
    )?
    """

    _overall_re = re.compile(overall_rules, re.X)

    def __init__(self, _iri=None, _quoted=True, scheme=None, authority=None, path=None, query=None, fragment=None):
        """
        :param _iri: A full IRI as a str
        :param scheme: Scheme part of the IRI, overrides the same part of the IRI.
        :param authority: Authority part of the IRI, overrides the same part of the IRI.
        :param path: Path part of the IRI, overrides the same part of the IRI.
        :param query: Query part of the IRI, overrides the same part of the IRI.
        :param fragment: Fragment part of the IRI, overrides the same part of the IRI.
        """

        if isinstance(_iri, Iri):
            _scheme = _iri.scheme

            _authority = _iri._authority
            # Need to copy IriAuthority, not immutable
            if _authority is not None:
                _authority = IriAuthority(_authority)

            _path = _iri._path
            # Need to copy IriPath, not immutable
            if _path is not None:
                _path = IriPath(_path)

            _query = _iri._query
            _fragment = _iri._fragment

        elif _iri:
            match = self._overall_re.match(str(_iri))
            if not match:
                raise ValueError("Input does not look like an IRI")

            _scheme = match.group("scheme")
            if _scheme is not None:
                _scheme = str(_scheme).lower()

            _authority = match.group("authority")
            if _authority is not None:
                _authority = IriAuthority(_authority, _quoted)

            _path = match.group("path")
            if _path is not None:
                _path = IriPath(_path, _quoted)

            _query = match.group("query")
            if _query is not None:
                _query = IriQuery(_query, _quoted)

            _fragment = match.group("fragment")
            if _fragment is not None:
                _fragment = IriFragment(_fragment, _quoted)

        else:
            _scheme = _authority = _path = _query = _fragment = None

        if scheme is not None:
            self.scheme = scheme
        else:
            self._scheme = _scheme

        if authority is not None:
            self.authority = authority
        else:
            self._authority = _authority

        if path is not None:
            self.path = path
        else:
            self._path = _path

        if query is not None:
            self.query = query
        else:
            self._query = _query

        if fragment is not None:
            self.fragment = fragment
        else:
            self._fragment = _fragment

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other

        if isinstance(other, Iri):
            if self._scheme != other._scheme:
                return False
            if self._authority != other._authority:
                return False
            if self._path != other._path:
                return False
            if self._query != other._query:
                return False
            if self._fragment != other._fragment:
                return False
            return True

        return NotImplemented

    def __repr__(self):
        return "{}(scheme={!r}, authority={!r}, path={!r}, query={!r}, fragment={!r})".format(
            self.__class__.__name__, self.scheme, self._authority, self._path, self._query, self._fragment
        )

    def __str__(self):
        ret = []

        if self.scheme:
            ret.extend((self.scheme, ":"))

        authority = self._authority
        if authority is not None:
            ret.extend(("//", authority.fullquoted))

        path = self._path
        if path is not None:
            ret.append(path.fullquoted)

        query = self._query
        if query is not None:
            ret.extend(("?", query.fullquoted))

        fragment = self._fragment
        if fragment is not None:
            ret.extend(("#", fragment.fullquoted))

        return "".join(ret)

    def __add__(self, other):
        if isinstance(other, Iri):
            new_scheme = other.scheme
            new_authority = other.authority
            new_path = other.path
            new_query = other.query

            if new_scheme is None:
                new_scheme = self.scheme

                if new_authority is None:
                    new_authority = self.authority

                    if not new_path:
                        new_path = self.path

                        if new_query is None:
                            new_query = self.query
                    else:
                        new_path = self.path + new_path

            return Iri(
                scheme=new_scheme, authority=new_authority, path=new_path, query=new_query, fragment=other.fragment
            )

        if isinstance(other, str):
            return self + Iri(other)

        return NotImplemented

    def __del_scheme(self):
        self._scheme = None

    def __get_scheme(self):
        return self._scheme

    def __set_scheme(self, value):
        self._scheme = str(value).lower()

    scheme = property(__get_scheme, __set_scheme, __del_scheme, """Scheme part of the IRI.""")

    def __del_authority(self):
        self._authority = None

    def __get_authority(self):
        return self._authority

    def __set_authority(self, value):
        if value.__class__ is not IriAuthority:
            value = IriAuthority(value, False)
        self._authority = value

    authority = property(__get_authority, __set_authority, __del_authority, """Authority part of the IRI.""")

    def __del_path(self):
        self._path = None

    def __get_path(self):
        return self._path

    def __set_path(self, value):
        if value.__class__ is not IriPath:
            value = IriPath(value, False)
        self._path = value

    path = property(__get_path, __set_path, __del_path, """Path part of the IRI.""")

    def __del_query(self):
        self._query = None

    def __get_query(self):
        return self._query

    def __set_query(self, value):
        self._query = IriQuery(value, False)

    query = property(__get_query, __set_query, __del_query, """Query part of the IRI.""")

    def __del_fragment(self):
        self._fragment = None

    def __get_fragment(self):
        return self._fragment

    def __set_fragment(self, value):
        self._fragment = IriFragment(value, False)

    fragment = property(__get_fragment, __set_fragment, __del_fragment, """Fragment part of the IRI.""")


class _Value(str):
    __slots__ = "_quoted"

    # Rules for quoting parts of the IRI.
    quote_rules_iri = (
        """((?:%[0-9a-fA-F]{2})+)|"""
        """([^-!$&'*+.0123456789=ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz|"""
        """\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]+)"""
    )
    quote_rules_uri = (
        """((?:%[0-9a-fA-F]{2})+)|"""
        """([^-!$&'*+.0123456789=ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz|"""
        """]+)"""
    )
    quote_filter = frozenset()

    _quote_re_iri = re.compile(quote_rules_iri)
    _quote_re_uri = re.compile(quote_rules_uri)

    # Matches consecutive percent-encoded values
    unquote_rules = r"(%[0-9a-fA-F]{2})+"
    _unquote_re = re.compile(unquote_rules)

    def __new__(cls, input, _quoted=True):
        # This object is immutable, no need to copy it
        if isinstance(input, cls):
            return input

        if _quoted:
            input, input_quoted = cls._unquote(input)
        else:
            input_quoted = None

        ret = str.__new__(cls, input)
        ret._quoted = input_quoted
        return ret

    @classmethod
    def _quote(cls, input, url=False, requote=False):
        """
        Quote all illegal characters.

        :param input: the string to quote
        :param url: True for URI, False for IRI
        :param requote: Input string is already quoted
        :returns: Quoted string
        """
        quote_filter = cls.quote_filter

        def subrepl(match):
            t_quoted = match.group(1)
            t_plain = match.group(2)

            if t_quoted:
                if not requote:
                    t_quoted = t_quoted.replace("%", "%25")
                return t_quoted

            return "".join(
                char if char in quote_filter else "".join("%%%02X" % b for b in char.encode("utf-8"))
                for char in t_plain
            )

        re = url and cls._quote_re_uri or cls._quote_re_iri
        return re.sub(subrepl, input)

    @classmethod
    def _unquote(cls, s):
        """
        Unquotes percent-encoded strings.

        :param s: Input string
        :returns: Tuple of full decoded and minimal quoted string
        """
        ret1 = []
        ret2 = []
        pos = 0

        for match in cls._unquote_re.finditer(s):
            # Handle leading text
            t = s[pos : match.start()]
            ret1.append(t)
            ret2.append(t)
            pos = match.end()

            part = []
            for item in match.group().split("%")[1:]:
                part.append(int(item, 16))
            part = bytes(part)
            ret1.append(part.decode("utf-8", "replace"))
            ret2.append(part.replace(b"%", b"%25").decode("utf-8", "iriquote"))

        # Handle trailing text
        t = s[pos:]
        ret1.append(t)
        ret2.append(t)
        return "".join(ret1), "".join(ret2)

    @property
    def fullquoted(self):
        """
        Full quoted form of the IRI part.

        All characters which are illegal in the part are encoded.
        Used to generate the full IRI.
        """
        if self._quoted is not None:
            return self._quote(self._quoted, requote=True)
        return self._quote(self)

    @property
    def quoted(self):
        """
        Minimal quoted form of the IRI part.

        Only '%' and illegal UTF-8 sequences are encoded. Primarily used to
        have a one-to-one mapping with non-UTF-8 URIs.
        """
        if self._quoted is not None:
            return self._quoted
        return self.replace("%", "%25")

    @property
    def urlquoted(self):
        """
        URI quoted form of the IRI part.

        All characters which are illegal in the part are encoded.
        Used to generate the full URI.
        """
        if self._quoted is not None:
            return self._quote(self._quoted, url=True, requote=True)
        return self._quote(self, url=True)


class IriAuthority(AutoNe):
    authority_rules = r"""
    ^
    (
        (?P<userinfo>
            [^@]*
        )
        @
    )?
    (?P<host>
        .*?
    )
    (
        :
        (?P<port>
            \d*
        )
    )?
    $
    """

    _authority_re = re.compile(authority_rules, re.X)

    def __init__(self, iri_authority=None, _quoted=True, userinfo=None, host=None, port=None):
        self._userinfo = self._host = self.port = None

        if iri_authority:
            if isinstance(iri_authority, IriAuthority):
                self._userinfo = iri_authority._userinfo
                self._host = iri_authority._host
                self.port = iri_authority.port
            else:
                self._parse(iri_authority, _quoted)

        if userinfo is not None:
            self.userinfo = userinfo
        if host is not None:
            self.host = host
        if userinfo is not None:
            self.port = port

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other
        if isinstance(other, IriAuthority):
            return self._userinfo == other._userinfo and self._host == other._host and self.port == other.port
        return NotImplemented

    def __bool__(self):
        if self._userinfo or self._host or self.port:
            return True
        return False

    def __repr__(self):
        return "{}(userinfo={!r}, host={!r}, port={!r})".format(
            self.__class__.__name__, self._userinfo, self._host, self.port
        )

    def __str__(self):
        return self.__get(self._userinfo, self._host)

    def __get(self, userinfo, host):
        ret = []

        if userinfo is not None:
            ret.extend((userinfo, "@"))
        if host is not None:
            ret.append(host)
        if self.port is not None:
            ret.append(":")
            if self.port:
                ret.append(str(self.port))

        return "".join(ret)

    def _parse(self, iri_authority, quoted):
        match = self._authority_re.match(iri_authority)

        if not match:
            raise ValueError("Input does not look like an IRI authority")

        userinfo = match.group("userinfo")
        if userinfo is not None:
            self._userinfo = IriAuthorityUserinfo(userinfo, quoted)

        host = match.group("host")
        if host is not None:
            self._host = IriAuthorityHost(host, quoted)

        port = match.group("port")
        if port is not None:
            if port:
                self.port = int(port)
            else:
                self.port = 0

    @property
    def fullquoted(self):
        """
        Full quoted form of the authority part of the IRI.

        All characters which are illegal in the authority part are encoded.
        Used to generate the full IRI.
        """
        userinfo = self._userinfo and self._userinfo.fullquoted
        host = self._host and self._host.fullquoted
        return self.__get(userinfo, host)

    @property
    def quoted(self):
        """
        Minimal quoted form of the authority part of the IRI.

        Only '%' and illegal UTF-8 sequences are encoded. Primarily used to
        have a one-to-one mapping with non-UTF-8 URIs.
        """
        userinfo = self._userinfo and self._userinfo.quoted
        host = self._host and self._host.quoted
        return self.__get(userinfo, host)

    @property
    def urlquoted(self):
        """
        URI quoted form of the authority part of the IRI.

        All characters which are illegal in the authority part are encoded.
        Used to generate the full URI.
        """
        userinfo = self._userinfo and self._userinfo.urlquoted
        host = self._host and self._host.urlquoted
        return self.__get(userinfo, host)

    def __del_userinfo(self):
        self._userinfo = None

    def __get_userinfo(self):
        return self._userinfo

    def __set_userinfo(self, value):
        self._userinfo = IriAuthorityUserinfo(value, False)

    userinfo = property(__get_userinfo, __set_userinfo, __del_userinfo)

    def __del_host(self):
        self._host = None

    def __get_host(self):
        return self._host

    def __set_host(self, value):
        self._host = IriAuthorityHost(value, False)

    host = property(__get_host, __set_host, __del_host)


class IriAuthorityUserinfo(_Value):
    pass


class IriAuthorityHost(_Value):
    pass


class IriPath(AutoNe):
    __slots__ = "_list"

    def __init__(self, iri_path=None, _quoted=True):
        self._list = []

        if iri_path:
            if isinstance(iri_path, IriPath):
                self._list = iri_path._list[:]
            elif isinstance(iri_path, (tuple, list)):
                self._list = [IriPathSegment(i, False) for i in iri_path]
            else:
                _list = [IriPathSegment(i, _quoted) for i in iri_path.split("/")]
                self._list = self._remove_dots(_list)

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other
        if isinstance(other, IriPath):
            return self._list == other._list
        return NotImplemented

    def __getitem__(self, key):
        ret = self._list[key]
        if isinstance(key, slice):
            return self.__class__(ret)
        return ret

    def __len__(self):
        return len(self._list)

    def __bool__(self):
        return bool(self._list)

    def __add__(self, other):
        if isinstance(other, (str, list, tuple)):
            return self + IriPath(other, False)

        if isinstance(other, IriPath):
            if other._list and other._list[0] == "":
                segments = other._list
            else:
                segments = self._list[:-1] + other._list
            return IriPath(self._remove_dots(segments))

        return NotImplemented

    def __str__(self):
        return "/".join(self._list)

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, str(self))

    def _remove_dots(self, segments):
        if not segments or segments[0] != "":
            return segments

        empty = segments[0]

        output = []
        remove = 0

        # Get reversed list with first (empty) element removed
        for i in segments[:0:-1]:
            if i == ".":
                if not output:
                    output.insert(0, empty)
            elif i == "..":
                if not output:
                    output.insert(0, empty)
                remove += 1
            else:
                if remove:
                    remove -= 1
                else:
                    output.insert(0, i)

        output.insert(0, empty)
        return output

    def extend(self, value):
        self._list.extend(IriPathSegment(i) for i in value)

    @property
    def fullquoted(self):
        """
        Full quoted form of the path part of the IRI.

        All characters which are illegal in the path part are encoded.
        Used to generate the full IRI.
        """
        return "/".join(i.fullquoted for i in self._list)

    @property
    def quoted(self):
        """
        Minimal quoted form of the path part of the IRI.

        Only '%' and illegal UTF-8 sequences are encoded. Primarily used to
        have a one-to-one mapping with non-UTF-8 URIs.
        """
        return "/".join(i.quoted for i in self._list)

    @property
    def urlquoted(self):
        """
        URI quoted form of the path part of the IRI.

        All characters which are illegal in the path part are encoded.
        Used to generate the full URI.
        """
        return "/".join(i.urlquoted for i in self._list)


class IriPathSegment(_Value):
    quote_filter = frozenset("@:/")


class IriQuery(_Value):
    quote_filter = frozenset("@:/?")


class IriFragment(_Value):
    quote_filter = frozenset("@:/?")
