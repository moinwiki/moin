"""
MoinMoin - tests for moin.macros.MailTo.
"""

from moin.macros.MailTo import Macro
from moin.utils.tree import xlink
from flask import g as flaskg


def test_mailto_no_arguments():
    """Test no arguments."""
    macro_object = Macro()
    arguments = []
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    test_res = list(res.attrib.values())
    assert "error" in test_res[0]


def test_mailto_too_many_arguments():
    """Test too many arguments."""
    macro_object = Macro()
    arguments = ["extra, argument, arg2"]
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    test_res = list(res.attrib.values())
    assert "error" in test_res[0]


def test_mailto_short_email():
    """Test short email."""
    macro_object = Macro()
    arguments = ["ab"]
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    test_res = list(res.attrib.values())
    assert "error" in test_res[0]


def test_mailto_valid_login(_req_ctx):
    """Test valid login."""
    macro_object = Macro()
    arguments = ["user AT example DOT org"]
    flaskg.user.valid = True
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    assert res.attrib[xlink.href] == "mailto:user@example.org"


def test_mailto_valid_login_with_text(_req_ctx):
    """Test valid email with logged-in user and display text."""
    macro_object = Macro()
    arguments = ["user AT example DOT org,Mail me"]
    flaskg.user.valid = True
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    assert res.attrib[xlink.href] == "mailto:user@example.org"
    assert "Mail me" in list(res)


def test_mailto_anonymous(_req_ctx):
    """Test valid email with anonymous user."""
    macro_object = Macro()
    arguments = ["user AT example DOT org"]
    flaskg.user.valid = False
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    assert "<user AT example DOT org>" in list(res)


def test_mailto_anonymous_with_text(_req_ctx):
    """Test valid email with anonymous user and display text."""
    macro_object = Macro()
    arguments = ["user AT example DOT org,write me"]
    flaskg.user.valid = False
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    children = list(res)
    assert "write me " in children
    assert "<user AT example DOT org>" in children


def test_extra_whitespace(_req_ctx):
    """Test extra whitespace."""
    macro_object = Macro()
    arguments = [" user  AT example  DOT org,write me "]
    flaskg.user.valid = True
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    assert res.attrib[xlink.href] == "mailto:user@example.org"


def test_extra_uppercase(_req_ctx):
    """Test extra uppercase."""
    macro_object = Macro()
    arguments = [" user  AT UPPER example  DOT CASE org"]
    flaskg.user.valid = True
    res = macro_object.macro("content", arguments, "page_url", "alternative")
    assert res.attrib[xlink.href] == "mailto:user@example.org"
