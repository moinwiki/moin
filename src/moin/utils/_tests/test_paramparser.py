# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.utils.paramparser Tests
"""


import pytest

from moin.utils import paramparser


class TestParamParsing:
    def testMacroArgs(self):
        abcd = ["a", "b", "c", "d"]
        abcd_dict = {"a": "1", "b": "2", "c": "3", "d": "4"}
        tests = [
            # regular and quoting tests
            ("d = 4,c=3,b=2,a= 1 ", ([], abcd_dict, [])),
            ("a,b,c,d", (abcd, {}, [])),
            (" a , b , c , d ", (abcd, {}, [])),
            ("   a   ", (["a"], {}, [])),
            ('"  a  "', (["  a  "], {}, [])),
            ('a,b,c,d, "a,b,c,d"', (abcd + ["a,b,c,d"], {}, [])),
            ('quote " :), b', (['quote " :)', "b"], {}, [])),
            ('"quote "" :)", b', (['quote " :)', "b"], {}, [])),
            ("=7", ([], {"": "7"}, [])),
            (",,", ([None, None, None], {}, [])),
            (',"",', ([None, "", None], {}, [])),
            (',"", ""', ([None, "", ""], {}, [])),
            ('  ""  ,"", ""', (["", "", ""], {}, [])),
            # some name=value test
            ("d = 4,c=3,b=2,a= 1 ", ([], abcd_dict, [])),
            ('d=d,e="a,b,c,d"', ([], {"d": "d", "e": "a,b,c,d"}, [])),
            ('d = d,e = "a,b,c,d"', ([], {"d": "d", "e": "a,b,c,d"}, [])),
            ('d = d, e = "a,b,c,d"', ([], {"d": "d", "e": "a,b,c,d"}, [])),
            ('d = , e = "a,b,c,d"', ([], {"d": None, "e": "a,b,c,d"}, [])),
            ('d = "", e = "a,b,c,d"', ([], {"d": "", "e": "a,b,c,d"}, [])),
            ('d = "", e = ', ([], {"d": "", "e": None}, [])),
            ('d=""', ([], {"d": ""}, [])),
            ('d = "", e = ""', ([], {"d": "", "e": ""}, [])),
            # no, None as key isn't accepted
            (' = "",  e = ""', ([], {"": "", "e": ""}, [])),
            # can quote both name and value:
            ('d = d," e "= "a,b,c,d"', ([], {"d": "d", " e ": "a,b,c,d"}, [])),
            # trailing args
            ("1,2,a=b,3,4", (["1", "2"], {"a": "b"}, ["3", "4"])),
            # can quote quotes:
            ('d = """d"', ([], {"d": '"d'}, [])),
            ('d = """d"""', ([], {"d": '"d"'}, [])),
            ('d = "d"" ", e=7', ([], {"d": 'd" ', "e": "7"}, [])),
            ('d = "d""", e=8', ([], {"d": 'd"', "e": "8"}, [])),
        ]
        for args, expected in tests:
            result = paramparser.parse_quoted_separated(args)
            assert expected == result
            for val in result[0]:
                assert val is None or isinstance(val, str)
            for val in result[1].keys():
                assert val is None or isinstance(val, str)
            for val in result[1].values():
                assert val is None or isinstance(val, str)
            for val in result[2]:
                assert val is None or isinstance(val, str)

    def testLimited(self):
        tests = [
            # regular and quoting tests
            ("d = 4,c=3,b=2,a= 1 ", ([], {"d": "4", "c": "3,b=2,a= 1"}, [])),
            ("a,b,c,d", (["a", "b,c,d"], {}, [])),
            ("a=b,b,c,d", ([], {"a": "b"}, ["b,c,d"])),
        ]
        for args, expected in tests:
            result = paramparser.parse_quoted_separated(args, seplimit=1)
            assert expected == result
            for val in result[0]:
                assert val is None or isinstance(val, str)
            for val in result[1].keys():
                assert val is None or isinstance(val, str)
            for val in result[1].values():
                assert val is None or isinstance(val, str)
            for val in result[2]:
                assert val is None or isinstance(val, str)

    @pytest.mark.parametrize(
        "args,expected",
        [
            # regular and quoting tests
            ("d==4,=3 ", ([], {"d": "=4", "": "3"}, [])),
            ("===a,b,c,d", ([], {"": "==a"}, ["b", "c", "d"])),
            ("a,b,===,c,d", (["a", "b"], {"": "=="}, ["c", "d"])),
        ],
    )
    def testDoubleNameValueSeparator(self, args, expected):
        result = paramparser.parse_quoted_separated(args)
        assert result == expected

    def testNoNameValue(self):
        abcd = ["a", "b", "c", "d"]
        tests = [
            # regular and quoting tests
            ("d = 4,c=3,b=2,a= 1 ", ["d = 4", "c=3", "b=2", "a= 1"]),
            ("a,b,c,d", abcd),
            (" a , b , c , d ", abcd),
            ("   a   ", ["a"]),
            ('"  a  "', ["  a  "]),
            ('a,b,c,d, "a,b,c,d"', abcd + ["a,b,c,d"]),
            ('quote " :), b', ['quote " :)', "b"]),
            ('"quote "" :)", b', ['quote " :)', "b"]),
            ('"unended quote', ['"unended quote']),
            ('"', ['"']),
            ('d=d,e="a,b,c,d"', ["d=d", 'e="a', "b", "c", 'd"']),
        ]
        for args, expected in tests:
            result = paramparser.parse_quoted_separated(args, name_value=False)
            assert expected == result
            for val in result:
                assert val is None or isinstance(val, str)

    def testUnitArgument(self):
        result = paramparser.UnitArgument("7mm", float, ["%", "mm"])
        assert result.get_default() == (7.0, "mm")
        assert result.parse_argument("8%") == (8.0, "%")
        pytest.raises(ValueError, result.parse_argument, "7m")
        pytest.raises(ValueError, result.parse_argument, "7")
        pytest.raises(ValueError, result.parse_argument, "mm")

    @pytest.mark.parametrize(
        "args,sep,kwsep,expected",
        [
            ('"a", "b", "c"', ",", None, ["a", "b", "c"]),
            ("a:b, b:c, c:d", ",", ":", [("a", "b"), ("b", "c"), ("c", "d")]),
            ("a:b, b:c, c:d", ",", None, ["a:b", "b:c", "c:d"]),
            ("a=b, b=c, c=d", ",", None, ["a=b", "b=c", "c=d"]),
            ("a=b, b=c, c=d", ",", "=", [("a", "b"), ("b", "c"), ("c", "d")]),
            ('"a"; "b"; "c"', ";", None, ["a", "b", "c"]),
            ("a:b; b:c; c:d", ";", ":", [("a", "b"), ("b", "c"), ("c", "d")]),
            ("a:b; b:c; c:d", ";", None, ["a:b", "b:c", "c:d"]),
            ("a=b; b=c; c=d", ";", None, ["a=b", "b=c", "c=d"]),
            ("a=b; b=c; c=d", ";", "=", [("a", "b"), ("b", "c"), ("c", "d")]),
            ('"a" "b" "c"', None, None, ["a", "b", "c"]),
            ('" a " "b" "c"', None, None, [" a ", "b", "c"]),
            ('"a  " "b" "c"', None, None, ["a  ", "b", "c"]),
            ('"  a" "b" "c"', None, None, ["  a", "b", "c"]),
            ('"  a" "b" "c"', None, ":", ["  a", "b", "c"]),
            ('"a:a" "b:b" "c:b"', None, ":", ["a:a", "b:b", "c:b"]),
            ("   a:a  ", None, ":", [None, None, None, ("a", "a"), None, None]),
            ("a a: a", None, ":", ["a", ("a", None), "a"]),
            ('a a:"b c d" a', None, ":", ["a", ("a", "b c d"), "a"]),
            ('a a:"b "" d" a', None, ":", ["a", ("a", 'b " d'), "a"]),
            ("title:Help* dog cat", None, ":", [("title", "Help*"), "dog", "cat"]),
            ('title:Help* "dog cat"', None, ":", [("title", "Help*"), "dog cat"]),
            ("a:b:c d:e:f", None, ":", [("a", "b:c"), ("d", "e:f")]),
            ("a:b:c:d", None, ":", [("a", "b:c:d")]),
        ],
    )
    def testExtendedParser(self, args, sep, kwsep, expected):
        res = paramparser.parse_quoted_separated_ext(args, sep, kwsep)
        assert res == expected

    @pytest.mark.parametrize(
        "args,sep,kwsep,expected",
        [
            ('"a", "b", "c"', ",", None, ["a", "b", "c"]),
            ('("a", "b", "c")', ",", None, [["(", "a", "b", "c"]]),
            ('("a"("b", "c"))', ",", None, [["(", "a", ["(", "b", "c"]]]),
            ('("a"("b)))", "c"))', ",", None, [["(", "a", ["(", "b)))", "c"]]]),
            ('("a"("b>>> ( ab )>", "c"))', ",", None, [["(", "a", ["(", "b>>> ( ab )>", "c"]]]),
            ('("a" ("b" "c"))', None, None, [["(", "a", ["(", "b", "c"]]]),
            ('("a"("b", "c") ) ', ",", None, [["(", "a", ["(", "b", "c"]]]),
            ('("a", <"b", ("c")>)', ",", None, [["(", "a", ["<", "b", ["(", "c"]]]]),
            (",,,(a, b, c)", ",", None, [None, None, None, ["(", "a", "b", "c"]]),
        ],
    )
    def testExtendedParserBracketing(self, args, sep, kwsep, expected):
        res = paramparser.parse_quoted_separated_ext(args, sep, kwsep, brackets=("<>", "()"))
        assert res == expected

    @pytest.mark.parametrize(
        "args,quotes,expected",
        [
            ('"a b" -a b-', '"', ["a b", "-a", "b-"]),
            ('"a b" -a b-', "-", ['"a', 'b"', "a b"]),
            ('"a b" -a b-', '"-', ["a b", "a b"]),
            ('"a- b" -a b-', '"-', ["a- b", "a b"]),
            ('"a- b" -a" b-', '"-', ["a- b", 'a" b']),
        ],
    )
    def testExtendedParserQuoting(self, args, quotes, expected):
        res = paramparser.parse_quoted_separated_ext(args, quotes=quotes)
        assert res == expected

    @pytest.mark.parametrize(
        "args,sep,kwsep,expected",
        [
            ('"a", "b", "c"', ",", None, ["a", "b", "c"]),
            ("a:b, b:c, c:d", ",", ":", [("a", "b"), ("b", "c"), ("c", "d")]),
            ("a:b, b:c, c:d", ",", None, ["a:b", "b:c", "c:d"]),
            ("a=b, b=c, c=d", ",", None, ["a=b", "b=c", "c=d"]),
            ("a=b, b=c, c=d", ",", "=", [("a", "b"), ("b", "c"), ("c", "d")]),
            ('"a"; "b"; "c"', ";", None, ["a", "b", "c"]),
            ("a:b; b:c; c:d", ";", ":", [("a", "b"), ("b", "c"), ("c", "d")]),
            ("a:b; b:c; c:d", ";", None, ["a:b", "b:c", "c:d"]),
            ("a=b; b=c; c=d", ";", None, ["a=b", "b=c", "c=d"]),
            ("a=b; b=c; c=d", ";", "=", [("a", "b"), ("b", "c"), ("c", "d")]),
            ('"a" "b" "c"', None, None, ["a", "b", "c"]),
            ('" a " "b" "c"', None, None, [" a ", "b", "c"]),
            ('"a  " "b" "c"', None, None, ["a  ", "b", "c"]),
            ('"  a" "b" "c"', None, None, ["  a", "b", "c"]),
            ('"  a" "b" "c"', None, ":", ["  a", "b", "c"]),
            ('"a:a" "b:b" "c:b"', None, ":", ["a:a", "b:b", "c:b"]),
            ("   a:a  ", None, ":", [None, None, None, ("a", "a"), None, None]),
            ("a a: a", None, ":", ["a", ("a", None), "a"]),
            ('a a:"b c d" a', None, ":", ["a", ("a", "b c d"), "a"]),
            ('a a:"b "" d" a', None, ":", ["a", ("a", 'b " d'), "a"]),
            ("title:Help* dog cat", None, ":", [("title", "Help*"), "dog", "cat"]),
            ('title:Help* "dog cat"', None, ":", [("title", "Help*"), "dog cat"]),
            ("a:b:c d:e:f", None, ":", [("a", "b", "c"), ("d", "e", "f")]),
            ("a:b:c:d", None, ":", [("a", "b", "c", "d")]),
            ('a:"b:c":d', None, ":", [("a", "b:c", "d")]),
        ],
    )
    def testExtendedParserMultikey(self, args, sep, kwsep, expected):
        res = paramparser.parse_quoted_separated_ext(args, sep, kwsep, multikey=True)
        assert res == expected

    P = paramparser.ParserPrefix("+")
    M = paramparser.ParserPrefix("-")

    @pytest.mark.parametrize(
        "args,sep,kwsep,expected",
        [
            ('"a", "b", "c"', ",", None, ["a", "b", "c"]),
            ("a:b, b:c, c:d", ",", ":", [("a", "b"), ("b", "c"), ("c", "d")]),
            ("a:b, b:c, c:d", ",", None, ["a:b", "b:c", "c:d"]),
            ("a=b, b=c, c=d", ",", None, ["a=b", "b=c", "c=d"]),
            ("a=b, b=c, c=d", ",", "=", [("a", "b"), ("b", "c"), ("c", "d")]),
            ('"a"; "b"; "c"', ";", None, ["a", "b", "c"]),
            ("a:b; b:c; c:d", ";", ":", [("a", "b"), ("b", "c"), ("c", "d")]),
            ("a:b; b:c; c:d", ";", None, ["a:b", "b:c", "c:d"]),
            ("a=b; b=c; c=d", ";", None, ["a=b", "b=c", "c=d"]),
            ("a=b; b=c; c=d", ";", "=", [("a", "b"), ("b", "c"), ("c", "d")]),
            ('"a" "b" "c"', None, None, ["a", "b", "c"]),
            ('" a " "b" "c"', None, None, [" a ", "b", "c"]),
            ('"a  " "b" "c"', None, None, ["a  ", "b", "c"]),
            ('"  a" "b" "c"', None, None, ["  a", "b", "c"]),
            ('"  a" "b" "c"', None, ":", ["  a", "b", "c"]),
            ('"a:a" "b:b" "c:b"', None, ":", ["a:a", "b:b", "c:b"]),
            ("   a:a  ", None, ":", [None, None, None, ("a", "a"), None, None]),
            ("a a: a", None, ":", ["a", ("a", None), "a"]),
            ('a a:"b c d" a', None, ":", ["a", ("a", "b c d"), "a"]),
            ('a a:"b "" d" a', None, ":", ["a", ("a", 'b " d'), "a"]),
            ("title:Help* dog cat", None, ":", [("title", "Help*"), "dog", "cat"]),
            ('title:Help* "dog cat"', None, ":", [("title", "Help*"), "dog cat"]),
            ("a:b:c d:e:f", None, ":", [("a", "b", "c"), ("d", "e", "f")]),
            ("a:b:c:d", None, ":", [("a", "b", "c", "d")]),
            ('a:"b:c":d', None, ":", [("a", "b:c", "d")]),
            ("-a:b:d", None, ":", [(M, "a", "b", "d")]),
            ('"-a:b:d"', None, ":", [("-a:b:d")]),
            ('-"a:b:d"', None, ":", [(M, "a:b:d")]),
            ('-a:"b:c":"d e f g"', None, ":", [(M, "a", "b:c", "d e f g")]),
            ("+-a:b:d", None, ":", [(P, "-a", "b", "d")]),
            ('-"+a:b:d"', None, ":", [(M, "+a:b:d")]),
            # bit of a weird case...
            ('-+"a:b:d"', None, ":", [(M, '+"a', "b", 'd"')]),
            ('-a:"b:c" a +b', None, ":", [(M, "a", "b:c"), "a", (P, "b")]),
        ],
    )
    def testExtendedParserPrefix(self, args, sep, kwsep, expected):
        res = paramparser.parse_quoted_separated_ext(args, sep, kwsep, multikey=True, prefixes="-+")
        assert res == expected

    UCE = paramparser.BracketUnexpectedCloseError
    MCE = paramparser.BracketMissingCloseError

    @pytest.mark.parametrize(
        "args,sep,kwsep,err",
        [
            ('("a", "b", "c"', ",", None, MCE),
            ('("a"("b", "c")', ",", None, MCE),
            ('("a"<"b", "c")>', ",", None, UCE),
            (')("a" ("b" "c"))', None, None, UCE),
            ('("a", ("b", "c">))', ",", None, UCE),
            ('("a", ("b", <"c">>))', ",", None, UCE),
            ("(<(<)>)>", ",", None, UCE),
        ],
    )
    def testExtendedParserBracketingErrors(self, args, sep, kwsep, err):
        pytest.raises(err, paramparser.parse_quoted_separated_ext, args, sep, kwsep, brackets=("<>", "()"))


class TestArgGetters:
    def testGetBoolean(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, False, False),
            (None, None, True, True),
            # some real values
            ("0", None, None, False),
            ("1", None, None, True),
            ("false", None, None, False),
            ("true", None, None, True),
            ("FALSE", None, None, False),
            ("TRUE", None, None, True),
            ("no", None, None, False),
            ("yes", None, None, True),
            ("NO", None, None, False),
            ("YES", None, None, True),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_bool(arg, name, default) == expected

    def testGetBooleanRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_bool, None, None, 42)

        # anything except None or str raises TypeError
        pytest.raises(TypeError, paramparser.get_bool, True)
        pytest.raises(TypeError, paramparser.get_bool, 42)
        pytest.raises(TypeError, paramparser.get_bool, 42.0)
        pytest.raises(TypeError, paramparser.get_bool, b"")
        pytest.raises(TypeError, paramparser.get_bool, tuple())
        pytest.raises(TypeError, paramparser.get_bool, [])
        pytest.raises(TypeError, paramparser.get_bool, {})

        # any value not convertable to boolean raises ValueError
        pytest.raises(ValueError, paramparser.get_bool, "")
        pytest.raises(ValueError, paramparser.get_bool, "42")
        pytest.raises(ValueError, paramparser.get_bool, "wrong")
        pytest.raises(ValueError, paramparser.get_bool, '"True"')  # must not be quoted!

    def testGetInt(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, -23, -23),
            (None, None, 42, 42),
            # some real values
            ("0", None, None, 0),
            ("42", None, None, 42),
            ("-23", None, None, -23),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_int(arg, name, default) == expected

    def testGetIntRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_int, None, None, 42.23)

        # anything except None or str raises TypeError
        pytest.raises(TypeError, paramparser.get_int, True)
        pytest.raises(TypeError, paramparser.get_int, 42)
        pytest.raises(TypeError, paramparser.get_int, 42.0)
        pytest.raises(TypeError, paramparser.get_int, b"")
        pytest.raises(TypeError, paramparser.get_int, tuple())
        pytest.raises(TypeError, paramparser.get_int, [])
        pytest.raises(TypeError, paramparser.get_int, {})

        # any value not convertable to int raises ValueError
        pytest.raises(ValueError, paramparser.get_int, "")
        pytest.raises(ValueError, paramparser.get_int, "23.42")
        pytest.raises(ValueError, paramparser.get_int, "wrong")
        pytest.raises(ValueError, paramparser.get_int, '"4711"')  # must not be quoted!

    def testGetFloat(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, -23.42, -23.42),
            (None, None, 42.23, 42.23),
            # some real values
            ("0", None, None, 0),
            ("42.23", None, None, 42.23),
            ("-23.42", None, None, -23.42),
            ("-23.42E3", None, None, -23.42e3),
            ("23.42E-3", None, None, 23.42e-3),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_float(arg, name, default) == expected

    def testGetFloatRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_float, None, None, "42")

        # anything except None or str raises TypeError
        pytest.raises(TypeError, paramparser.get_float, True)
        pytest.raises(TypeError, paramparser.get_float, 42)
        pytest.raises(TypeError, paramparser.get_float, 42.0)
        pytest.raises(TypeError, paramparser.get_float, b"")
        pytest.raises(TypeError, paramparser.get_float, tuple())
        pytest.raises(TypeError, paramparser.get_float, [])
        pytest.raises(TypeError, paramparser.get_float, {})

        # any value not convertable to int raises ValueError
        pytest.raises(ValueError, paramparser.get_float, "")
        pytest.raises(ValueError, paramparser.get_float, "wrong")
        pytest.raises(ValueError, paramparser.get_float, '"47.11"')  # must not be quoted!

    def testGetComplex(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, -23.42, -23.42),
            (None, None, 42.23, 42.23),
            # some real values
            ("0", None, None, 0),
            ("42.23", None, None, 42.23),
            ("-23.42", None, None, -23.42),
            ("-23.42E3", None, None, -23.42e3),
            ("23.42E-3", None, None, 23.42e-3),
            ("23.42E-3+3.04j", None, None, 23.42e-3 + 3.04j),
            ("3.04j", None, None, 3.04j),
            ("-3.04j", None, None, -3.04j),
            ("23.42E-3+3.04i", None, None, 23.42e-3 + 3.04j),
            ("3.04i", None, None, 3.04j),
            ("-3.04i", None, None, -3.04j),
            ("-3", None, None, -3),
            ("-300000000000000000000", None, None, -300000000000000000000),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_complex(arg, name, default) == expected

    def testGetComplexRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_complex, None, None, "42")

        # anything except None or str raises TypeError
        pytest.raises(TypeError, paramparser.get_complex, True)
        pytest.raises(TypeError, paramparser.get_complex, 42)
        pytest.raises(TypeError, paramparser.get_complex, 42.0)
        pytest.raises(TypeError, paramparser.get_complex, 3j)
        pytest.raises(TypeError, paramparser.get_complex, b"")
        pytest.raises(TypeError, paramparser.get_complex, tuple())
        pytest.raises(TypeError, paramparser.get_complex, [])
        pytest.raises(TypeError, paramparser.get_complex, {})

        # any value not convertable to int raises ValueError
        pytest.raises(ValueError, paramparser.get_complex, "")
        pytest.raises(ValueError, paramparser.get_complex, "3jj")
        pytest.raises(ValueError, paramparser.get_complex, "3Ij")
        pytest.raises(ValueError, paramparser.get_complex, "3i-3i")
        pytest.raises(ValueError, paramparser.get_complex, "wrong")
        pytest.raises(ValueError, paramparser.get_complex, '"47.11"')  # must not be quoted!

    def testGetUnicode(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, "", ""),
            (None, None, "abc", "abc"),
            # some real values
            ("", None, None, ""),
            ("abc", None, None, "abc"),
            ('"abc"', None, None, '"abc"'),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_str(arg, name, default) == expected

    def testGetStrRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_str, None, None, 42)

        # anything except None or str raises TypeError
        pytest.raises(TypeError, paramparser.get_str, True)
        pytest.raises(TypeError, paramparser.get_str, 42)
        pytest.raises(TypeError, paramparser.get_str, 42.0)
        pytest.raises(TypeError, paramparser.get_str, b"")
        pytest.raises(TypeError, paramparser.get_str, tuple())
        pytest.raises(TypeError, paramparser.get_str, [])
        pytest.raises(TypeError, paramparser.get_str, {})


class TestExtensionInvoking:
    def _test_invoke_bool(self, b=bool):
        assert b is False

    def _test_invoke_bool_def(self, v=bool, b=False):
        assert b == v
        assert isinstance(b, bool)
        assert isinstance(v, bool)

    def _test_invoke_int_None(self, i=int):
        assert i == 1 or i is None

    def _test_invoke_float_None(self, i=float):
        assert i == 1.4 or i is None

    def _test_invoke_float_required(self, i=paramparser.required_arg(float)):
        assert i == 1.4

    def _test_invoke_choice(self, a, choice=["a", "b", "c"]):
        assert a == 7
        assert choice == "a"

    def _test_invoke_choicet(self, a, choice=("a", "b", "c")):
        assert a == 7
        assert choice == "a"

    def _test_invoke_choice_required(self, i=paramparser.required_arg(("b", "a"))):
        assert i == "a"

    def _test_trailing(self, a, _trailing_args=[]):
        assert _trailing_args == ["a"]

    def _test_arbitrary_kw(self, expect, _kwargs={}):
        assert _kwargs == expect

    def testInvoke(self):
        def _test_invoke_int(i=int):
            assert i == 1

        def _test_invoke_int_fixed(a, b, i=int):
            assert a == 7
            assert b == 8
            assert i == 1 or i is None

        ief = paramparser.invoke_extension_function
        ief(self._test_invoke_bool, "False")
        ief(self._test_invoke_bool, "b=False")
        ief(_test_invoke_int, "1")
        ief(_test_invoke_int, "i=1")
        ief(self._test_invoke_bool_def, "False, False")
        ief(self._test_invoke_bool_def, "b=False, v=False")
        ief(self._test_invoke_bool_def, "False")
        ief(self._test_invoke_int_None, "i=1")
        ief(self._test_invoke_int_None, "i=")
        ief(self._test_invoke_int_None, "")
        pytest.raises(ValueError, ief, self._test_invoke_int_None, "x")
        pytest.raises(ValueError, ief, self._test_invoke_int_None, '""')
        pytest.raises(ValueError, ief, self._test_invoke_int_None, 'i=""')
        pytest.raises(ValueError, ief, _test_invoke_int_fixed, "a=7", [7, 8])
        ief(_test_invoke_int_fixed, "i=1", [7, 8])
        pytest.raises(ValueError, ief, _test_invoke_int_fixed, 'i=""', [7, 8])
        ief(_test_invoke_int_fixed, "i=", [7, 8])

        for choicefn in (self._test_invoke_choice, self._test_invoke_choicet):
            ief(choicefn, "", [7])
            ief(choicefn, "choice=a", [7])
            ief(choicefn, "choice=", [7])
            ief(choicefn, 'choice="a"', [7])
            pytest.raises(ValueError, ief, choicefn, "x", [7])
            pytest.raises(ValueError, ief, choicefn, "choice=x", [7])

        ief(self._test_invoke_float_None, "i=1.4")
        ief(self._test_invoke_float_None, "i=")
        ief(self._test_invoke_float_None, "")
        ief(self._test_invoke_float_None, "1.4")
        pytest.raises(ValueError, ief, self._test_invoke_float_None, "x")
        pytest.raises(ValueError, ief, self._test_invoke_float_None, '""')
        pytest.raises(ValueError, ief, self._test_invoke_float_None, 'i=""')
        ief(self._test_trailing, "a=7, a")
        ief(self._test_trailing, "7, a")
        ief(self._test_arbitrary_kw, "test=x, \xc3=test", [{"\xc3": "test", "test": "x"}])
        ief(self._test_arbitrary_kw, 'test=x, "\xc3"=test', [{"\xc3": "test", "test": "x"}])
        ief(self._test_arbitrary_kw, 'test=x, "7 \xc3"=test', [{"7 \xc3": "test", "test": "x"}])
        ief(self._test_arbitrary_kw, "test=x, 7 \xc3=test", [{"7 \xc3": "test", "test": "x"}])
        ief(self._test_arbitrary_kw, "7 \xc3=test, test= x ", [{"7 \xc3": "test", "test": "x"}])
        pytest.raises(ValueError, ief, self._test_invoke_float_required, "")
        ief(self._test_invoke_float_required, "1.4")
        ief(self._test_invoke_float_required, "i=1.4")
        pytest.raises(ValueError, ief, self._test_invoke_choice_required, "")
        ief(self._test_invoke_choice_required, "a")
        ief(self._test_invoke_choice_required, "i=a")
        pytest.raises(ValueError, ief, self._test_invoke_float_required, ",")

    def testConstructors(self):
        ief = paramparser.invoke_extension_function

        # new style class
        class TEST1:
            def __init__(self, a=int):
                self.constructed = True
                assert a == 7

        class TEST2(TEST1):
            pass

        obj = ief(TEST1, "a=7")
        assert isinstance(obj, TEST1)
        assert obj.constructed
        pytest.raises(ValueError, ief, TEST1, "b")

        obj = ief(TEST2, "a=7")
        assert isinstance(obj, TEST1)
        assert isinstance(obj, TEST2)
        assert obj.constructed
        pytest.raises(ValueError, ief, TEST2, "b")

        # old style class
        class TEST3:
            def __init__(self, a=int):
                self.constructed = True
                assert a == 7

        class TEST4(TEST3):
            pass

        obj = ief(TEST3, "a=7")
        assert isinstance(obj, TEST3)
        assert obj.constructed
        pytest.raises(ValueError, ief, TEST3, "b")

        obj = ief(TEST4, "a=7")
        assert isinstance(obj, TEST3)
        assert isinstance(obj, TEST4)
        assert obj.constructed
        pytest.raises(ValueError, ief, TEST4, "b")

    def testFailing(self):
        ief = paramparser.invoke_extension_function

        pytest.raises(TypeError, ief, hex, "15")

    def testAllDefault(self):
        ief = paramparser.invoke_extension_function

        def has_many_defaults(a=1, b=2, c=3, d=4):
            assert a == 1
            assert b == 2
            assert c == 3
            assert d == 4
            return True

        assert ief(has_many_defaults, "1, 2, 3, 4")
        assert ief(has_many_defaults, "2, 3, 4", [1])
        assert ief(has_many_defaults, "3, 4", [1, 2])
        assert ief(has_many_defaults, "4", [1, 2, 3])
        assert ief(has_many_defaults, "", [1, 2, 3, 4])
        assert ief(has_many_defaults, "d=4,c=3,b=2,a=1")
        assert ief(has_many_defaults, "d=4,c=3,b=2", [1])
        assert ief(has_many_defaults, "d=4,c=3", [1, 2])
        assert ief(has_many_defaults, "d=4", [1, 2, 3])

    def testInvokeComplex(self):
        ief = paramparser.invoke_extension_function

        def has_complex(a=complex, b=complex):
            assert a == b
            return True

        assert ief(has_complex, "3-3i, 3-3j")
        assert ief(has_complex, "2i, 2j")
        assert ief(has_complex, "b=2i, a=2j")
        assert ief(has_complex, "2.007, 2.007")
        assert ief(has_complex, "2.007", [2.007])
        assert ief(has_complex, "b=2.007", [2.007])
