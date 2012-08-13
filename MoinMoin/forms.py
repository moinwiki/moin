# Copyright: 2012 MoinMoin:PavelSviderski
# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Flatland widgets

    General Flatland widgets containing hints for the templates.
"""


import re, datetime
import json

from flatland import Element, Form, String, Integer, Boolean, Enum, Dict, DateTime as _DateTime, JoinedString
from flatland.validation import Validator, Present, IsEmail, ValueBetween, URLValidator, Converted, ValueAtLeast
from flatland.exc import AdaptationError

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


class ValidJSON(Validator):
    """Validator for JSON
    """
    invalid_json_msg = L_('Invalid JSON.')

    def validate(self, element, state):
        try:
            json.loads(element.value)
        except: # catch ANY exception that happens due to unserializing
            return self.note_error(element, state, 'invalid_json_msg')
        return True

JSON = OptionalMultilineText.with_properties(lang='en', dir='ltr').validated_by(ValidJSON())

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


# Need a better name to capture the behavior
class MyJoinedString(JoinedString):
    """
    A JoinedString that offers the list of children (not the joined string) as
    value property.
    """
    @property
    def value(self):
        return [child.value for child in self]

    @property
    def u(self):
        return self.separator.join(child.u for child in self)

Tags = MyJoinedString.of(String).with_properties(widget=WIDGET_TEXT).using(label=L_('Tags'), optional=True, separator=', ', separator_regex=re.compile(r'\s*,\s*'))

Search = Text.using(default=u'', optional=True).with_properties(widget=WIDGET_SEARCH, placeholder=L_("Search Query"))

_Integer = Integer.validated_by(Converted())

AnyInteger = _Integer.with_properties(widget=WIDGET_ANY_INTEGER)

Natural = AnyInteger.validated_by(ValueAtLeast(0))

SmallNatural = _Integer.with_properties(widget=WIDGET_SMALL_NATURAL)


class DateTimeUNIX(_DateTime):
    """
    A DateTime that uses a UNIX timestamp instead of datetime as internal
    representation of DateTime.
    """
    def serialize(self, value):
        """Serializes value to string."""
        if isinstance(value, int):
            try:
                value = datetime.datetime.utcfromtimestamp(value)
            except ValueError:
                pass
        return super(DateTimeUNIX, self).serialize(value)

    def adapt(self, value):
        """Coerces value to a native UNIX timestamp.

        If value is an instance of int and it is a correct UNIX timestamp,
        returns it unchanged. Otherwise uses DateTime superclass to parse it.
        """
        if isinstance(value, int):
            try:
                # check if a value is a correct timestamp
                dt = datetime.datetime.utcfromtimestamp(value)
                return value
            except ValueError:
                raise AdaptationError()
        dt = super(DateTimeUNIX, self).adapt(value)
        if isinstance(dt, datetime.datetime):
            # XXX forces circular dependency when it is in the head import block
            from MoinMoin.themes import utctimestamp
            # TODO: Add support for timezones
            dt = utctimestamp(dt)
        return dt

DateTime = (DateTimeUNIX.with_properties(widget=WIDGET_DATETIME, placeholder=_("YYYY-MM-DD HH:MM:SS (example: 2999-12-31 23:59:59)"))
            .validated_by(Converted(incorrect=L_("Please use the following format: YYYY-MM-DD HH:MM:SS"))))

File = FileStorage.with_properties(widget=WIDGET_FILE)

Submit = String.using(default=L_('OK'), optional=True).with_properties(widget=WIDGET_SUBMIT, class_=CLASS_BUTTON)

Hidden = String.using(optional=True).with_properties(widget=WIDGET_HIDDEN)
