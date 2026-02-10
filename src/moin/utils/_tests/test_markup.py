# Copyright: 2026 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.markup tests.
"""

import pytest
from markupsafe import Markup
from moin.utils.markup import safe_markup


def test_safe_markup_return_markup():
    html = "<ins>text added</ins>"
    result = safe_markup(html)

    assert isinstance(result, Markup)
    assert result == html


def test_safe_markup_accept_markup():
    html = Markup("<del>text removed</del>")
    result = safe_markup(html)

    assert result is html


def test_safe_markup_reject_non_string():
    with pytest.raises(TypeError):
        safe_markup(123)
