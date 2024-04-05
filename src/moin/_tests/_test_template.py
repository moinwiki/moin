# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007 MoinMoin:AlexanderSchremmer
# Copyright: 2009 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.module_tested Tests

    Module names must start with 'test_' to be included in the tests.
"""


# include here the module that you want to test:
from moin import module_tested


class TestSimpleStuff:
    """The simplest MoinMoin test class

    Class name must start with 'Test' to be included in
    the tests.

    See http://codespeak.net/py/dist/test.html for reference.
    """

    def testSimplest(self):
        """module_tested: test description...

        Function name MUST start with 'test' to be included in the
        tests.
        """
        result = module_tested.some_function("test_value")
        expected = "expected value"
        assert result == expected


class TestComplexStuff:
    """Describe these tests here...

    Some tests may have a list of tests related to this test case. You
    can add a test by adding another line to this list
    """

    _tests = (
        # description, test, expected
        ("Line break", "<<BR>>", "<br>"),
    )

    from moin._tests import wikiconfig

    class Config(wikiconfig.Config):
        foo = "bar"  # we want to have this non-default setting

    def setup_class(self):
        """Stuff that should be run to init the state of this test class"""

    def teardown_class(self):
        """Stuff that should run to clean up the state of this test class"""

    def testFunction(self):
        """module_tested: function should..."""
        for description, test, expected in self._tests:
            result = self._helper_function(test)
            assert result == expected

    def _helper_fuction(self, test):
        """Some tests needs extra  work to run

        Keep the test non interesting details out of the way.
        """
        module_tested.do_this()
        module_tested.do_that()
        result = None
        return result
