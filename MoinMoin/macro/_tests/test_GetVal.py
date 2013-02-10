# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macro.GetVal
"""

from flask import g as flaskg

from MoinMoin.macro.GetVal import *
from MoinMoin.constants.keys import SOMEDICT
from MoinMoin._tests import become_trusted, update_item
from MoinMoin.conftest import init_test_app, deinit_test_app
from MoinMoin._tests import wikiconfig
import pytest
DATA = "This is a dict item."

class TestMacro(object):
    """ Test: GetVal.Macro """

    def setup_method(self, method):
        # temporary hack till we apply test cleanup mechanism on tests.
        self.app, self.ctx = init_test_app(wikiconfig.Config)
        become_trusted()
        somedict = {u"One": u"1",
                    u"Two": u"2"}
        update_item(u'TestDict', {SOMEDICT: somedict}, DATA)

    def teardown_method(self, method):
        deinit_test_app(self.app, self.ctx)

    def test_Macro(self):
        macro_obj = Macro()
        arguments = [u'TestDict']
        with pytest.raises(ValueError):
            macro_obj.macro('content', arguments, 'page_url', 'alternative')

        # add the second element to arguments
        arguments.append(u'One')

        if not flaskg.user.may.read(arguments[0]):
            with pytest.raises(ValueError):
                macro_obj.macro('content', arguments, 'page_url', 'alternative')

        result = macro_obj.macro('content', arguments, 'page_url', 'alternative')
        assert result == u'1'

        # change the value of second element
        arguments[1] = u'Two'
        result = macro_obj.macro('content', arguments, 'page_url', 'alternative')
        assert result == u'2'
