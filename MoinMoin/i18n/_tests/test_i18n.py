# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for i18n
"""

from MoinMoin.i18n import get_locale, get_timezone
import pytest

from MoinMoin.i18n import _, L_, N_

def test_user_attributes():
    test_locale = get_locale()
    assert test_locale == 'en'

    test_timezone = get_timezone()
    assert test_timezone == 'UTC'

def test_text():
    # test for gettext
    result = _('test_text')
    assert result == 'test_text'

    # test for lazy_gettext
    result = L_('test_lazy_text')
    assert result == u'test_lazy_text'

    # test for ngettext
    result1 = N_('text1', 'text2', 1)
    assert result1 == 'text1'
    result2 = N_('text1', 'text2', 2)
    assert result2 == 'text2'

