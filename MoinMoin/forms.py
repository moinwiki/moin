# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Flatland widgets

    General Flatland widgets containing hints for the templates.
"""


from functools import reduce
from operator import add

from flatland import Element, Form, String, Integer, Boolean, Enum, MultiValue, Dict
from flatland.validation import Validator, Present, IsEmail, ValueBetween, URLValidator, Converted, ValueAtLeast

from MoinMoin.constants.forms import *
from MoinMoin.i18n import _, L_, N_
from MoinMoin.security.textcha import TextCha, TextChaizedForm, TextChaValid
from MoinMoin.util.forms import FileStorage


Text = String.with_properties(widget=WIDGET_TEXT)

MultilineText = String.with_properties(widget=WIDGET_MULTILINE_TEXT)

OptionalText = Text.using(optional=True)

RequiredText = Text.validated_by(Present())

OptionalMultilineText = MultilineText.using(optional=True)

RequiredMultilineText = MultilineText.validated_by(Present())

URL = String.with_properties(widget=WIDGET_TEXT).validated_by(URLValidator())

OpenID = URL.using(label=L_('OpenID')).with_properties(placeholder=L_("OpenID address"))

YourOpenID = OpenID.with_properties(placeholder=L_("Your OpenID address"))

Email = String.using(label=L_('E-Mail')).with_properties(widget=WIDGET_EMAIL, placeholder=L_("E-Mail address")).validated_by(IsEmail())

YourEmail = Email.with_properties(placeholder=L_("Your E-Mail address"))

Password = Text.with_properties(widget=WIDGET_PASSWORD).using(label=L_('Password'))

RequiredPassword = Password.validated_by(Present())

Checkbox = Boolean.with_properties(widget=WIDGET_CHECKBOX).using(optional=True, default=1)

InlineCheckbox = Checkbox.with_properties(widget=WIDGET_INLINE_CHECKBOX)

Select = Enum.with_properties(widget=WIDGET_SELECT)

# XXX Need a better one than plain text box
Tags = MultiValue.of(String).with_properties(widget=WIDGET_TEXT).using(label=L_('Tags'), optional=True)

Search = Text.using(default=u'', optional=True).with_properties(widget=WIDGET_SEARCH, placeholder=L_("Search Query"))

_Integer = Integer.validated_by(Converted())

AnyInteger = _Integer.with_properties(widget=WIDGET_ANY_INTEGER)

Natural = AnyInteger.validated_by(ValueAtLeast(0))

SmallNatural = _Integer.with_properties(widget=WIDGET_SMALL_NATURAL)

File = FileStorage.with_properties(widget=WIDGET_FILE)

Submit = String.using(default=L_('OK'), optional=True).with_properties(widget=WIDGET_SUBMIT, class_=CLASS_BUTTON)

Hidden = String.using(optional=True).with_properties(widget=WIDGET_HIDDEN)
