# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.forms Tests
"""

from moin.utils import forms


class Bind:
    """class for self defined test_bind attributes"""

    def __init__(self):
        self.label = "test_content"
        self.default_value = "test_bind_default"
        self.optional = True
        self.properties = {"autofocus": False, "placeholder": None}
        self.errors = None


test_bind = Bind()

test_attributes = {"type": "submit", "required": "test_required", "autofocus": None, "placeholder": None}


def test_label_filter():
    # when content is None
    result1 = forms.label_filter("test_tagname", test_attributes, None, "test_context", test_bind)
    expected = "test_content"
    assert result1 == expected

    # when content is not None
    result2 = forms.label_filter("test_tagname", test_attributes, "new_content", "test_context", test_bind)
    expected = "new_content"
    assert result2 == expected


def test_button_filter():
    result = forms.button_filter("test_tagname", test_attributes, "new_content", "test_context", None)
    expected = "new_content"
    assert result == expected

    # attributes.get('type') in ['submit', 'reset', ])
    content_result = forms.button_filter("input", test_attributes, "new_content", "test_context", test_bind)
    expected = "new_content"
    assert content_result == expected
    attributes_result = test_attributes["value"]
    expected = "test_bind_default"
    assert attributes_result == expected

    # tagname == 'button'
    content_result = forms.button_filter("button", test_attributes, None, "test_context", test_bind)
    expected = "test_bind_default"
    assert content_result == expected


def test_required_filter():
    test_bind.optional = False
    test_attributes["class"] = "test_class"
    content_result = forms.required_filter("test_tagname", test_attributes, "new_content", "test_context", test_bind)
    expected = "new_content"
    assert content_result == expected
    # fixing a class for the form element, restricts the HTML we can generate
    # attribute_result = test_attributes['class']
    # expected = 'required'
    # assert attribute_result == expected

    # tagname == 'input'
    content_result = forms.required_filter("input", test_attributes, "new_content", "test_context", test_bind)
    expected = "new_content"
    assert content_result == expected
    attribute_result = test_attributes["required"]
    expected = "required"
    assert attribute_result == expected


def test_autofocus_filter():
    test_bind.properties = {"autofocus": True}
    content_result = forms.autofocus_filter("test_tagname", test_attributes, "new_content", "test_context", test_bind)
    assert content_result == "new_content"
    attribute_result = test_attributes["autofocus"]
    assert attribute_result == "autofocus"


def test_placeholder_filter():
    test_bind.properties["placeholder"] = "test_placeholder"
    content_result = forms.placeholder_filter("test_tagname", test_attributes, "new_content", "test_context", test_bind)
    assert content_result == "new_content"
    attribute_result = test_attributes["placeholder"]
    assert attribute_result == "test_placeholder"


def test_error_filter_factory():
    # when 'class' not in test_attributes
    test_bind.errors = "test_errors"
    test_attributes.pop("class")
    test_fun_returned = forms.error_filter_factory("test_moin_error")
    content_result = test_fun_returned("test_tagname", test_attributes, "new_content", "test_context", test_bind)
    assert content_result == "new_content"
    attribute_result = test_attributes["class"]
    assert attribute_result == "test_moin_error"

    # class in test_attributes
    test_attributes["class"] = "test_attribute_class"
    content_result = test_fun_returned("test_tagname", test_attributes, "new_content", "test_context", test_bind)
    assert content_result == "new_content"
    attribute_result = test_attributes["class"]
    expected = "test_attribute_class test_moin_error"
    assert attribute_result == expected
