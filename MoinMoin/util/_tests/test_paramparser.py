# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.paramparser Tests
"""


import pytest

from MoinMoin.util import paramparser


class TestParamParsing(object):
    def testMacroArgs(self):
        abcd = [u'a', u'b', u'c', u'd']
        abcd_dict = {u'a': u'1', u'b': u'2', u'c': u'3', u'd': u'4'}
        tests = [
                  # regular and quoting tests
                  (u'd = 4,c=3,b=2,a= 1 ',    ([], abcd_dict, [])),
                  (u'a,b,c,d',                (abcd, {}, [])),
                  (u' a , b , c , d ',        (abcd, {}, [])),
                  (u'   a   ',                ([u'a'], {}, [])),
                  (u'"  a  "',                ([u'  a  '], {}, [])),
                  (u'a,b,c,d, "a,b,c,d"',     (abcd + [u'a,b,c,d'], {}, [])),
                  (u'quote " :), b',          ([u'quote " :)', u'b'], {}, [])),
                  (u'"quote "" :)", b',       ([u'quote " :)', u'b'], {}, [])),
                  (u'=7',                     ([], {u'': u'7'}, [])),
                  (u',,',                     ([None, None, None], {}, [])),
                  (u',"",',                   ([None, u'', None], {}, [])),
                  (u',"", ""',                ([None, u'', u''], {}, [])),
                  (u'  ""  ,"", ""',          ([u'', u'', u''], {}, [])),
                  # some name=value test
                  (u'd = 4,c=3,b=2,a= 1 ',    ([], abcd_dict, [])),
                  (u'd=d,e="a,b,c,d"',        ([], {u'd': u'd',
                                                    u'e': u'a,b,c,d'}, [])),
                  (u'd = d,e = "a,b,c,d"',    ([], {u'd': u'd',
                                                    u'e': u'a,b,c,d'}, [])),
                  (u'd = d, e = "a,b,c,d"',   ([], {u'd': u'd',
                                                    u'e': u'a,b,c,d'}, [])),
                  (u'd = , e = "a,b,c,d"',    ([], {u'd': None,
                                                    u'e': u'a,b,c,d'}, [])),
                  (u'd = "", e = "a,b,c,d"',  ([], {u'd': u'',
                                                    u'e': u'a,b,c,d'}, [])),
                  (u'd = "", e = ',           ([], {u'd': u'', u'e': None},
                                               [])),
                  (u'd=""',                   ([], {u'd': u''}, [])),
                  (u'd = "", e = ""',         ([], {u'd': u'', u'e': u''},
                                               [])),
                  # no, None as key isn't accepted
                  (u' = "",  e = ""',         ([], {u'': u'', u'e': u''},
                                               [])),
                  # can quote both name and value:
                  (u'd = d," e "= "a,b,c,d"', ([], {u'd': u'd',
                                                    u' e ': u'a,b,c,d'}, [])),
                  # trailing args
                  (u'1,2,a=b,3,4',            ([u'1', u'2'], {u'a': u'b'},
                                               [u'3', u'4'])),
                  # can quote quotes:
                  (u'd = """d"',              ([], {u'd': u'"d'}, [])),
                  (u'd = """d"""',            ([], {u'd': u'"d"'}, [])),
                  (u'd = "d"" ", e=7',        ([], {u'd': u'd" ', u'e': u'7'},
                                               [])),
                  (u'd = "d""", e=8',         ([], {u'd': u'd"', u'e': u'8'},
                                               [])),
                ]
        for args, expected in tests:
            result = paramparser.parse_quoted_separated(args)
            assert expected == result
            for val in result[0]:
                assert val is None or isinstance(val, unicode)
            for val in result[1].keys():
                assert val is None or isinstance(val, unicode)
            for val in result[1].values():
                assert val is None or isinstance(val, unicode)
            for val in result[2]:
                assert val is None or isinstance(val, unicode)

    def testLimited(self):
        tests = [
                  # regular and quoting tests
                  (u'd = 4,c=3,b=2,a= 1 ',    ([], {u'd': u'4',
                                                    u'c': u'3,b=2,a= 1'}, [])),
                  (u'a,b,c,d',                ([u'a', u'b,c,d'], {}, [])),
                  (u'a=b,b,c,d',              ([], {u'a': u'b'}, [u'b,c,d'])),
                ]
        for args, expected in tests:
            result = paramparser.parse_quoted_separated(args, seplimit=1)
            assert expected == result
            for val in result[0]:
                assert val is None or isinstance(val, unicode)
            for val in result[1].keys():
                assert val is None or isinstance(val, unicode)
            for val in result[1].values():
                assert val is None or isinstance(val, unicode)
            for val in result[2]:
                assert val is None or isinstance(val, unicode)

    def testDoubleNameValueSeparator(self):
        tests = [
                  # regular and quoting tests
                  (u'd==4,=3 ',    ([], {u'd': u'=4', u'': u'3'}, [])),
                  (u'===a,b,c,d',  ([], {u'': u'==a'}, [u'b', u'c', u'd'])),
                  (u'a,b,===,c,d', ([u'a', u'b'], {u'': u'=='}, [u'c', u'd'])),
                ]

        def _check(a, e):
            r = paramparser.parse_quoted_separated(a)
            assert r == e

        for args, expected in tests:
            yield _check, args, expected

    def testNoNameValue(self):
        abcd = [u'a', u'b', u'c', u'd']
        tests = [
                  # regular and quoting tests
                  (u'd = 4,c=3,b=2,a= 1 ',    [u'd = 4', u'c=3',
                                               u'b=2', u'a= 1']),
                  (u'a,b,c,d',                abcd),
                  (u' a , b , c , d ',        abcd),
                  (u'   a   ',                [u'a']),
                  (u'"  a  "',                [u'  a  ']),
                  (u'a,b,c,d, "a,b,c,d"',     abcd + [u'a,b,c,d']),
                  (u'quote " :), b',          [u'quote " :)', u'b']),
                  (u'"quote "" :)", b',       [u'quote " :)', u'b']),
                  (u'"unended quote',         [u'"unended quote']),
                  (u'"',                      [u'"']),
                  (u'd=d,e="a,b,c,d"',        [u'd=d', u'e="a', u'b',
                                               u'c', u'd"']),
                ]
        for args, expected in tests:
            result = paramparser.parse_quoted_separated(args, name_value=False)
            assert expected == result
            for val in result:
                assert val is None or isinstance(val, unicode)

    def testUnitArgument(self):
        result = paramparser.UnitArgument('7mm', float, ['%', 'mm'])
        assert result.get_default() == (7.0, 'mm')
        assert result.parse_argument('8%') == (8.0, '%')
        pytest.raises(ValueError, result.parse_argument, u'7m')
        pytest.raises(ValueError, result.parse_argument, u'7')
        pytest.raises(ValueError, result.parse_argument, u'mm')

    def testExtendedParser(self):
        tests = [
            (u'"a", "b", "c"', u',', None, [u'a', u'b', u'c']),
            (u'a:b, b:c, c:d', u',', u':', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'a:b, b:c, c:d', u',', None, [u'a:b', u'b:c', u'c:d']),
            (u'a=b, b=c, c=d', u',', None, [u'a=b', u'b=c', u'c=d']),
            (u'a=b, b=c, c=d', u',', u'=', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'"a"; "b"; "c"', u';', None, [u'a', u'b', u'c']),
            (u'a:b; b:c; c:d', u';', u':', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'a:b; b:c; c:d', u';', None, [u'a:b', u'b:c', u'c:d']),
            (u'a=b; b=c; c=d', u';', None, [u'a=b', u'b=c', u'c=d']),
            (u'a=b; b=c; c=d', u';', u'=', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'"a" "b" "c"', None, None, [u'a', u'b', u'c']),
            (u'" a " "b" "c"', None, None, [u' a ', u'b', u'c']),
            (u'"a  " "b" "c"', None, None, [u'a  ', u'b', u'c']),
            (u'"  a" "b" "c"', None, None, [u'  a', u'b', u'c']),
            (u'"  a" "b" "c"', None, u':', [u'  a', u'b', u'c']),
            (u'"a:a" "b:b" "c:b"', None, u':', [u'a:a', u'b:b', u'c:b']),
            (u'   a:a  ', None, u':', [None, None, None, (u'a', u'a'), None, None]),
            (u'a a: a', None, u':', [u'a', (u'a', None), u'a']),
            (u'a a:"b c d" a', None, u':', [u'a', (u'a', u'b c d'), u'a']),
            (u'a a:"b "" d" a', None, u':', [u'a', (u'a', u'b " d'), u'a']),
            (u'title:Help* dog cat', None, u':', [(u'title', u'Help*'), u'dog', u'cat']),
            (u'title:Help* "dog cat"', None, u':', [(u'title', u'Help*'), u'dog cat']),
            (u'a:b:c d:e:f', None, u':', [(u'a', u'b:c'), (u'd', 'e:f')]),
            (u'a:b:c:d', None, u':', [(u'a', u'b:c:d')]),
        ]

        def _check(args, sep, kwsep, expected):
            res = paramparser.parse_quoted_separated_ext(args, sep, kwsep)
            assert res == expected

        for test in tests:
            yield [_check] + list(test)

    def testExtendedParserBracketing(self):
        tests = [
            (u'"a", "b", "c"', u',', None, [u'a', u'b', u'c']),
            (u'("a", "b", "c")', u',', None, [[u'(', u'a', u'b', u'c']]),
            (u'("a"("b", "c"))', u',', None, [[u'(', u'a', [u'(', u'b', u'c']]]),
            (u'("a"("b)))", "c"))', u',', None, [[u'(', u'a', [u'(', u'b)))', u'c']]]),
            (u'("a"("b>>> ( ab )>", "c"))', u',', None, [[u'(', u'a', [u'(', u'b>>> ( ab )>', u'c']]]),
            (u'("a" ("b" "c"))', None, None, [[u'(', u'a', [u'(', u'b', u'c']]]),
            (u'("a"("b", "c") ) ', u',', None, [[u'(', u'a', [u'(', u'b', u'c']]]),
            (u'("a", <"b", ("c")>)', u',', None, [[u'(', u'a', [u'<', u'b', [u'(', u'c']]]]),
            (u',,,(a, b, c)', u',', None, [None, None, None, [u'(', u'a', u'b', u'c']]),
        ]

        def _check(args, sep, kwsep, expected):
            res = paramparser.parse_quoted_separated_ext(args, sep, kwsep, brackets=(u'<>', u'()'))
            assert res == expected

        for test in tests:
            yield [_check] + list(test)

    def testExtendedParserQuoting(self):
        tests = [
            (u'"a b" -a b-', u'"', [u'a b', u'-a', u'b-']),
            (u'"a b" -a b-', u"-", [u'"a', u'b"', u'a b']),
            (u'"a b" -a b-', u'"-', [u'a b', u'a b']),
            (u'"a- b" -a b-', u'"-', [u'a- b', u'a b']),
            (u'"a- b" -a" b-', u'"-', [u'a- b', u'a" b']),
        ]

        def _check(args, quotes, expected):
            res = paramparser.parse_quoted_separated_ext(args, quotes=quotes)
            assert res == expected

        for test in tests:
            yield [_check] + list(test)

    def testExtendedParserMultikey(self):
        tests = [
            (u'"a", "b", "c"', u',', None, [u'a', u'b', u'c']),
            (u'a:b, b:c, c:d', u',', u':', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'a:b, b:c, c:d', u',', None, [u'a:b', u'b:c', u'c:d']),
            (u'a=b, b=c, c=d', u',', None, [u'a=b', u'b=c', u'c=d']),
            (u'a=b, b=c, c=d', u',', u'=', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'"a"; "b"; "c"', u';', None, [u'a', u'b', u'c']),
            (u'a:b; b:c; c:d', u';', u':', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'a:b; b:c; c:d', u';', None, [u'a:b', u'b:c', u'c:d']),
            (u'a=b; b=c; c=d', u';', None, [u'a=b', u'b=c', u'c=d']),
            (u'a=b; b=c; c=d', u';', u'=', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'"a" "b" "c"', None, None, [u'a', u'b', u'c']),
            (u'" a " "b" "c"', None, None, [u' a ', u'b', u'c']),
            (u'"a  " "b" "c"', None, None, [u'a  ', u'b', u'c']),
            (u'"  a" "b" "c"', None, None, [u'  a', u'b', u'c']),
            (u'"  a" "b" "c"', None, u':', [u'  a', u'b', u'c']),
            (u'"a:a" "b:b" "c:b"', None, u':', [u'a:a', u'b:b', u'c:b']),
            (u'   a:a  ', None, u':', [None, None, None, (u'a', u'a'), None, None]),
            (u'a a: a', None, u':', [u'a', (u'a', None), u'a']),
            (u'a a:"b c d" a', None, u':', [u'a', (u'a', u'b c d'), u'a']),
            (u'a a:"b "" d" a', None, u':', [u'a', (u'a', u'b " d'), u'a']),
            (u'title:Help* dog cat', None, u':', [(u'title', u'Help*'), u'dog', u'cat']),
            (u'title:Help* "dog cat"', None, u':', [(u'title', u'Help*'), u'dog cat']),
            (u'a:b:c d:e:f', None, u':', [(u'a', u'b', u'c'), (u'd', 'e', u'f')]),
            (u'a:b:c:d', None, u':', [(u'a', u'b', u'c', u'd')]),
            (u'a:"b:c":d', None, u':', [(u'a', u'b:c', u'd')]),
        ]

        def _check(args, sep, kwsep, expected):
            res = paramparser.parse_quoted_separated_ext(args, sep, kwsep, multikey=True)
            assert res == expected

        for test in tests:
            yield [_check] + list(test)

    def testExtendedParserPrefix(self):
        P = paramparser.ParserPrefix('+')
        M = paramparser.ParserPrefix('-')
        tests = [
            (u'"a", "b", "c"', u',', None, [u'a', u'b', u'c']),
            (u'a:b, b:c, c:d', u',', u':', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'a:b, b:c, c:d', u',', None, [u'a:b', u'b:c', u'c:d']),
            (u'a=b, b=c, c=d', u',', None, [u'a=b', u'b=c', u'c=d']),
            (u'a=b, b=c, c=d', u',', u'=', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'"a"; "b"; "c"', u';', None, [u'a', u'b', u'c']),
            (u'a:b; b:c; c:d', u';', u':', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'a:b; b:c; c:d', u';', None, [u'a:b', u'b:c', u'c:d']),
            (u'a=b; b=c; c=d', u';', None, [u'a=b', u'b=c', u'c=d']),
            (u'a=b; b=c; c=d', u';', u'=', [(u'a', u'b'), (u'b', u'c'), (u'c', u'd')]),
            (u'"a" "b" "c"', None, None, [u'a', u'b', u'c']),
            (u'" a " "b" "c"', None, None, [u' a ', u'b', u'c']),
            (u'"a  " "b" "c"', None, None, [u'a  ', u'b', u'c']),
            (u'"  a" "b" "c"', None, None, [u'  a', u'b', u'c']),
            (u'"  a" "b" "c"', None, u':', [u'  a', u'b', u'c']),
            (u'"a:a" "b:b" "c:b"', None, u':', [u'a:a', u'b:b', u'c:b']),
            (u'   a:a  ', None, u':', [None, None, None, (u'a', u'a'), None, None]),
            (u'a a: a', None, u':', [u'a', (u'a', None), u'a']),
            (u'a a:"b c d" a', None, u':', [u'a', (u'a', u'b c d'), u'a']),
            (u'a a:"b "" d" a', None, u':', [u'a', (u'a', u'b " d'), u'a']),
            (u'title:Help* dog cat', None, u':', [(u'title', u'Help*'), u'dog', u'cat']),
            (u'title:Help* "dog cat"', None, u':', [(u'title', u'Help*'), u'dog cat']),
            (u'a:b:c d:e:f', None, u':', [(u'a', u'b', u'c'), (u'd', 'e', u'f')]),
            (u'a:b:c:d', None, u':', [(u'a', u'b', u'c', u'd')]),
            (u'a:"b:c":d', None, u':', [(u'a', u'b:c', u'd')]),

            (u'-a:b:d', None, u':', [(M, u'a', u'b', u'd')]),
            (u'"-a:b:d"', None, u':', [(u'-a:b:d')]),
            (u'-"a:b:d"', None, u':', [(M, u'a:b:d')]),
            (u'-a:"b:c":"d e f g"', None, u':', [(M, u'a', u'b:c', u'd e f g')]),
            (u'+-a:b:d', None, u':', [(P, u'-a', u'b', u'd')]),
            (u'-"+a:b:d"', None, u':', [(M, u'+a:b:d')]),
            # bit of a weird case...
            (u'-+"a:b:d"', None, u':', [(M, u'+"a', u'b', u'd"')]),
            (u'-a:"b:c" a +b', None, u':', [(M, u'a', u'b:c'), u'a', (P, u'b')]),
        ]

        def _check(args, sep, kwsep, expected):
            res = paramparser.parse_quoted_separated_ext(args, sep, kwsep, multikey=True, prefixes='-+')
            assert res == expected

        for test in tests:
            yield [_check] + list(test)

    def testExtendedParserBracketingErrors(self):
        UCE = paramparser.BracketUnexpectedCloseError
        MCE = paramparser.BracketMissingCloseError
        tests = [
            (u'("a", "b", "c"', u',', None, MCE),
            (u'("a"("b", "c")', u',', None, MCE),
            (u'("a"<"b", "c")>', u',', None, UCE),
            (u')("a" ("b" "c"))', None, None, UCE),
            (u'("a", ("b", "c">))', u',', None, UCE),
            (u'("a", ("b", <"c">>))', u',', None, UCE),
            (u'(<(<)>)>', u',', None, UCE),
        ]

        def _check(args, sep, kwsep, err):
            pytest.raises(err,
                           paramparser.parse_quoted_separated_ext,
                           args, sep, kwsep,
                           brackets=(u'<>', u'()'))

        for test in tests:
            yield [_check] + list(test)


class TestArgGetters(object):
    def testGetBoolean(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, False, False),
            (None, None, True, True),

            # some real values
            (u'0', None, None, False),
            (u'1', None, None, True),
            (u'false', None, None, False),
            (u'true', None, None, True),
            (u'FALSE', None, None, False),
            (u'TRUE', None, None, True),
            (u'no', None, None, False),
            (u'yes', None, None, True),
            (u'NO', None, None, False),
            (u'YES', None, None, True),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_bool(arg, name, default) == expected

    def testGetBooleanRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_bool, None, None, 42)

        # anything except None or unicode raises TypeError
        pytest.raises(TypeError, paramparser.get_bool, True)
        pytest.raises(TypeError, paramparser.get_bool, 42)
        pytest.raises(TypeError, paramparser.get_bool, 42.0)
        pytest.raises(TypeError, paramparser.get_bool, '')
        pytest.raises(TypeError, paramparser.get_bool, tuple())
        pytest.raises(TypeError, paramparser.get_bool, [])
        pytest.raises(TypeError, paramparser.get_bool, {})

        # any value not convertable to boolean raises ValueError
        pytest.raises(ValueError, paramparser.get_bool, u'')
        pytest.raises(ValueError, paramparser.get_bool, u'42')
        pytest.raises(ValueError, paramparser.get_bool, u'wrong')
        pytest.raises(ValueError, paramparser.get_bool, u'"True"')  # must not be quoted!

    def testGetInt(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, -23, -23),
            (None, None, 42, 42),

            # some real values
            (u'0', None, None, 0),
            (u'42', None, None, 42),
            (u'-23', None, None, -23),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_int(arg, name, default) == expected

    def testGetIntRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_int, None, None, 42.23)

        # anything except None or unicode raises TypeError
        pytest.raises(TypeError, paramparser.get_int, True)
        pytest.raises(TypeError, paramparser.get_int, 42)
        pytest.raises(TypeError, paramparser.get_int, 42.0)
        pytest.raises(TypeError, paramparser.get_int, '')
        pytest.raises(TypeError, paramparser.get_int, tuple())
        pytest.raises(TypeError, paramparser.get_int, [])
        pytest.raises(TypeError, paramparser.get_int, {})

        # any value not convertable to int raises ValueError
        pytest.raises(ValueError, paramparser.get_int, u'')
        pytest.raises(ValueError, paramparser.get_int, u'23.42')
        pytest.raises(ValueError, paramparser.get_int, u'wrong')
        pytest.raises(ValueError, paramparser.get_int, u'"4711"')  # must not be quoted!

    def testGetFloat(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, -23.42, -23.42),
            (None, None, 42.23, 42.23),

            # some real values
            (u'0', None, None, 0),
            (u'42.23', None, None, 42.23),
            (u'-23.42', None, None, -23.42),
            (u'-23.42E3', None, None, -23.42E3),
            (u'23.42E-3', None, None, 23.42E-3),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_float(arg, name, default) == expected

    def testGetFloatRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_float, None, None, u'42')

        # anything except None or unicode raises TypeError
        pytest.raises(TypeError, paramparser.get_float, True)
        pytest.raises(TypeError, paramparser.get_float, 42)
        pytest.raises(TypeError, paramparser.get_float, 42.0)
        pytest.raises(TypeError, paramparser.get_float, '')
        pytest.raises(TypeError, paramparser.get_float, tuple())
        pytest.raises(TypeError, paramparser.get_float, [])
        pytest.raises(TypeError, paramparser.get_float, {})

        # any value not convertable to int raises ValueError
        pytest.raises(ValueError, paramparser.get_float, u'')
        pytest.raises(ValueError, paramparser.get_float, u'wrong')
        pytest.raises(ValueError, paramparser.get_float, u'"47.11"')  # must not be quoted!

    def testGetComplex(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, -23.42, -23.42),
            (None, None, 42.23, 42.23),

            # some real values
            (u'0', None, None, 0),
            (u'42.23', None, None, 42.23),
            (u'-23.42', None, None, -23.42),
            (u'-23.42E3', None, None, -23.42E3),
            (u'23.42E-3', None, None, 23.42E-3),
            (u'23.42E-3+3.04j', None, None, 23.42E-3 + 3.04j),
            (u'3.04j', None, None, 3.04j),
            (u'-3.04j', None, None, -3.04j),
            (u'23.42E-3+3.04i', None, None, 23.42E-3 + 3.04j),
            (u'3.04i', None, None, 3.04j),
            (u'-3.04i', None, None, -3.04j),
            (u'-3', None, None, -3L),
            (u'-300000000000000000000', None, None, -300000000000000000000L),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_complex(arg, name, default) == expected

    def testGetComplexRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_complex, None, None, u'42')

        # anything except None or unicode raises TypeError
        pytest.raises(TypeError, paramparser.get_complex, True)
        pytest.raises(TypeError, paramparser.get_complex, 42)
        pytest.raises(TypeError, paramparser.get_complex, 42.0)
        pytest.raises(TypeError, paramparser.get_complex, 3j)
        pytest.raises(TypeError, paramparser.get_complex, '')
        pytest.raises(TypeError, paramparser.get_complex, tuple())
        pytest.raises(TypeError, paramparser.get_complex, [])
        pytest.raises(TypeError, paramparser.get_complex, {})

        # any value not convertable to int raises ValueError
        pytest.raises(ValueError, paramparser.get_complex, u'')
        pytest.raises(ValueError, paramparser.get_complex, u'3jj')
        pytest.raises(ValueError, paramparser.get_complex, u'3Ij')
        pytest.raises(ValueError, paramparser.get_complex, u'3i-3i')
        pytest.raises(ValueError, paramparser.get_complex, u'wrong')
        pytest.raises(ValueError, paramparser.get_complex, u'"47.11"')  # must not be quoted!

    def testGetUnicode(self):
        tests = [
            # default testing for None value
            (None, None, None, None),
            (None, None, u'', u''),
            (None, None, u'abc', u'abc'),

            # some real values
            (u'', None, None, u''),
            (u'abc', None, None, u'abc'),
            (u'"abc"', None, None, u'"abc"'),
        ]
        for arg, name, default, expected in tests:
            assert paramparser.get_unicode(arg, name, default) == expected

    def testGetUnicodeRaising(self):
        # wrong default type
        pytest.raises(AssertionError, paramparser.get_unicode, None, None, 42)

        # anything except None or unicode raises TypeError
        pytest.raises(TypeError, paramparser.get_unicode, True)
        pytest.raises(TypeError, paramparser.get_unicode, 42)
        pytest.raises(TypeError, paramparser.get_unicode, 42.0)
        pytest.raises(TypeError, paramparser.get_unicode, '')
        pytest.raises(TypeError, paramparser.get_unicode, tuple())
        pytest.raises(TypeError, paramparser.get_unicode, [])
        pytest.raises(TypeError, paramparser.get_unicode, {})


class TestExtensionInvoking(object):
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

    def _test_invoke_choice(self, a, choice=[u'a', u'b', u'c']):
        assert a == 7
        assert choice == u'a'

    def _test_invoke_choicet(self, a, choice=(u'a', u'b', u'c')):
        assert a == 7
        assert choice == u'a'

    def _test_invoke_choice_required(self, i=paramparser.required_arg((u'b', u'a'))):
        assert i == u'a'

    def _test_trailing(self, a, _trailing_args=[]):
        assert _trailing_args == [u'a']

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
        ief(self._test_invoke_bool, u'False')
        ief(self._test_invoke_bool, u'b=False')
        ief(_test_invoke_int, u'1')
        ief(_test_invoke_int, u'i=1')
        ief(self._test_invoke_bool_def, u'False, False')
        ief(self._test_invoke_bool_def, u'b=False, v=False')
        ief(self._test_invoke_bool_def, u'False')
        ief(self._test_invoke_int_None, u'i=1')
        ief(self._test_invoke_int_None, u'i=')
        ief(self._test_invoke_int_None, u'')
        pytest.raises(ValueError, ief,
                       self._test_invoke_int_None, u'x')
        pytest.raises(ValueError, ief,
                       self._test_invoke_int_None, u'""')
        pytest.raises(ValueError, ief,
                       self._test_invoke_int_None, u'i=""')
        pytest.raises(ValueError, ief,
                       _test_invoke_int_fixed, u'a=7', [7, 8])
        ief(_test_invoke_int_fixed, u'i=1', [7, 8])
        pytest.raises(ValueError, ief,
                       _test_invoke_int_fixed, u'i=""', [7, 8])
        ief(_test_invoke_int_fixed, u'i=', [7, 8])

        for choicefn in (self._test_invoke_choice, self._test_invoke_choicet):
            ief(choicefn, u'', [7])
            ief(choicefn, u'choice=a', [7])
            ief(choicefn, u'choice=', [7])
            ief(choicefn, u'choice="a"', [7])
            pytest.raises(ValueError, ief,
                           choicefn, u'x', [7])
            pytest.raises(ValueError, ief,
                           choicefn, u'choice=x', [7])

        ief(self._test_invoke_float_None, u'i=1.4')
        ief(self._test_invoke_float_None, u'i=')
        ief(self._test_invoke_float_None, u'')
        ief(self._test_invoke_float_None, u'1.4')
        pytest.raises(ValueError, ief,
                       self._test_invoke_float_None, u'x')
        pytest.raises(ValueError, ief,
                       self._test_invoke_float_None, u'""')
        pytest.raises(ValueError, ief,
                       self._test_invoke_float_None, u'i=""')
        ief(self._test_trailing, u'a=7, a')
        ief(self._test_trailing, u'7, a')
        ief(self._test_arbitrary_kw, u'test=x, \xc3=test',
            [{u'\xc3': 'test', 'test': u'x'}])
        ief(self._test_arbitrary_kw, u'test=x, "\xc3"=test',
            [{u'\xc3': 'test', 'test': u'x'}])
        ief(self._test_arbitrary_kw, u'test=x, "7 \xc3"=test',
            [{u'7 \xc3': 'test', 'test': u'x'}])
        ief(self._test_arbitrary_kw, u'test=x, 7 \xc3=test',
            [{u'7 \xc3': 'test', 'test': u'x'}])
        ief(self._test_arbitrary_kw, u'7 \xc3=test, test= x ',
            [{u'7 \xc3': 'test', 'test': u'x'}])
        pytest.raises(ValueError, ief,
                       self._test_invoke_float_required, u'')
        ief(self._test_invoke_float_required, u'1.4')
        ief(self._test_invoke_float_required, u'i=1.4')
        pytest.raises(ValueError, ief,
                       self._test_invoke_choice_required, u'')
        ief(self._test_invoke_choice_required, u'a')
        ief(self._test_invoke_choice_required, u'i=a')
        pytest.raises(ValueError, ief,
                       self._test_invoke_float_required, u',')

    def testConstructors(self):
        ief = paramparser.invoke_extension_function

        # new style class
        class TEST1(object):
            def __init__(self, a=int):
                self.constructed = True
                assert a == 7

        class TEST2(TEST1):
            pass

        obj = ief(TEST1, u'a=7')
        assert isinstance(obj, TEST1)
        assert obj.constructed
        pytest.raises(ValueError, ief, TEST1, u'b')

        obj = ief(TEST2, u'a=7')
        assert isinstance(obj, TEST1)
        assert isinstance(obj, TEST2)
        assert obj.constructed
        pytest.raises(ValueError, ief, TEST2, u'b')

        # old style class
        class TEST3:
            def __init__(self, a=int):
                self.constructed = True
                assert a == 7

        class TEST4(TEST3):
            pass

        obj = ief(TEST3, u'a=7')
        assert isinstance(obj, TEST3)
        assert obj.constructed
        pytest.raises(ValueError, ief, TEST3, u'b')

        obj = ief(TEST4, u'a=7')
        assert isinstance(obj, TEST3)
        assert isinstance(obj, TEST4)
        assert obj.constructed
        pytest.raises(ValueError, ief, TEST4, u'b')

    def testFailing(self):
        ief = paramparser.invoke_extension_function

        pytest.raises(TypeError, ief, hex, u'15')
        pytest.raises(TypeError, ief, cmp, u'15')
        pytest.raises(AttributeError, ief, unicode, u'15')

    def testAllDefault(self):
        ief = paramparser.invoke_extension_function

        def has_many_defaults(a=1, b=2, c=3, d=4):
            assert a == 1
            assert b == 2
            assert c == 3
            assert d == 4
            return True

        assert ief(has_many_defaults, u'1, 2, 3, 4')
        assert ief(has_many_defaults, u'2, 3, 4', [1])
        assert ief(has_many_defaults, u'3, 4', [1, 2])
        assert ief(has_many_defaults, u'4', [1, 2, 3])
        assert ief(has_many_defaults, u'', [1, 2, 3, 4])
        assert ief(has_many_defaults, u'd=4,c=3,b=2,a=1')
        assert ief(has_many_defaults, u'd=4,c=3,b=2', [1])
        assert ief(has_many_defaults, u'd=4,c=3', [1, 2])
        assert ief(has_many_defaults, u'd=4', [1, 2, 3])

    def testInvokeComplex(self):
        ief = paramparser.invoke_extension_function

        def has_complex(a=complex, b=complex):
            assert a == b
            return True

        assert ief(has_complex, u'3-3i, 3-3j')
        assert ief(has_complex, u'2i, 2j')
        assert ief(has_complex, u'b=2i, a=2j')
        assert ief(has_complex, u'2.007, 2.007')
        assert ief(has_complex, u'2.007', [2.007])
        assert ief(has_complex, u'b=2.007', [2.007])
