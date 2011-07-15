# -*- coding: utf-8 -*-
# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.forms Tests
"""

from MoinMoin.util import forms
import pytest

class Bind:
    """ class for self defined test_bind attributes """
    def __init__(self):
        self.label = 'test_content'
        self.default_value = 'test_bind_default'
        self.optional = True
        self.properties = {'autofocus':False}
test_bind = Bind()

test_attributes = {'type':'submit', u'class':'test_class', u'required':'test_required', 'autofocus':None}

def test_label_filter():
    # when content is None
    result1 = forms.label_filter('test_tagname', test_attributes, None, 'test_context', test_bind)
    expected = 'test_content'
    assert result1 == expected

    # when content is not None
    result2 = forms.label_filter('test_tagname', test_attributes, 'new_content', 'test_context', test_bind)
    expected = 'new_content'
    assert result2 == expected

def test_button_filter():
    result = forms.button_filter('test_tagname', test_attributes, 'new_content', 'test_context', None)
    expected = 'new_content'
    assert result == expected

    # attributes.get('type') in ['submit', 'reset', ])
    content_result = forms.button_filter('input', test_attributes, 'new_content', 'test_context', test_bind)
    expected = 'new_content'
    assert content_result == expected 
    attributes_result = test_attributes['value']
    expected = 'test_bind_default'
    assert attributes_result == expected

    # tagname == 'button'
    content_result = forms.button_filter('button', test_attributes, None, 'test_context', test_bind)
    expected = 'test_bind_default'
    assert content_result == expected

def test_required_filter():
    test_bind.optional = False
    content_result = forms.required_filter('test_tagname', test_attributes, 'new_content', 'test_context', test_bind)
    expected = 'new_content'
    assert content_result == expected
    attribute_result = test_attributes[u'class']
    expected = u'required'
    assert attribute_result == expected

    # tagname == 'input'
    content_result = forms.required_filter('input', test_attributes, 'new_content', 'test_context', test_bind)
    expected = 'new_content'
    assert content_result == expected
    attribute_result = test_attributes[u'required']
    expected = u'required'
    assert attribute_result == expected

def test_autofocus_filter():
    test_bind.properties = {'autofocus':True}
    content_result = forms.autofocus_filter('test_tagname', test_attributes, 'new_content', 'test_context', test_bind)
    assert content_result == 'new_content'
    attribute_result = test_attributes[u'autofocus']
    assert attribute_result == u'autofocus'

