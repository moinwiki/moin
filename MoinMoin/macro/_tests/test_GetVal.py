# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macro.GetVal
"""

import pytest
from flask import g as flaskg

from MoinMoin.macro.GetVal import *
from MoinMoin.constants.keys import SOMEDICT
from MoinMoin._tests import become_trusted, update_item


class TestMacro(object):
    @pytest.fixture
    def test_dict(self):
        become_trusted()
        somedict = {u"One": u"1",
                    u"Two": u"2"}
        update_item(u'TestDict', {SOMEDICT: somedict}, "This is a dict item.")

        return u"TestDict"

    def test_Macro(self, test_dict):
        macro_obj = Macro()
        arguments = [test_dict]
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
