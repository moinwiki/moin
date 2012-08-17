# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macro.Date
"""

import time
from datetime import datetime

from flaskext.babel import format_date, format_datetime

from MoinMoin.macro.Date import MacroDateTimeBase, Macro
import pytest

class TestMacroDateTimeBase(object):
    def test_parse_time(self):
        MacroDateTimeBase_obj = MacroDateTimeBase()
        test_time_args = '2011-08-07T11:11:11+0533'
        result = MacroDateTimeBase_obj.parse_time(test_time_args)
        expected = 1312695491.0
        assert result == expected
        result = format_datetime(datetime.utcfromtimestamp(result))
        expected = u'Aug 7, 2011 5:38:11 AM'
        assert result == expected
        with pytest.raises(ValueError):
            # things after next 10,000 years can't be predicted
            MacroDateTimeBase_obj.parse_time('12011-08-07T11:11:11')

class TestMacro(object):
    def test_macro(self):
        macro_obj = Macro()
        # when arguments is None
        result = macro_obj.macro('content', None, 'page_url', 'alternative')
        test_time = time.time()
        test_time = format_date(datetime.utcfromtimestamp(test_time))
        assert result == test_time

        arguments = ['2011-08-07T11:11:11+0533', 'argument2']
        result = macro_obj.macro('content', arguments, 'page_url', 'alternative')
        expected = u'Aug 7, 2011'
        assert result == expected
