# Copyright: 2012 MoinMoin:PavelSviderski
# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Flatland widgets

    General Flatland widgets containing hints for the templates.
"""


import re
import datetime
import json
from operator import itemgetter

from flatland import (Element, Form, String, Integer, Boolean, Enum as BaseEnum, Dict, JoinedString, List, Array,
                      DateTime as _DateTime)
from flatland.util import class_cloner, Unspecified
from flatland.validation import Validator, Present, IsEmail, ValueBetween, URLValidator, Converted, ValueAtLeast
from flatland.exc import AdaptationError

from whoosh.query import Term, Or, Not, And

from flask import g as flaskg
from flask import current_app as app

from MoinMoin.constants.forms import *
from MoinMoin.constants.keys import ITEMID, NAME, LATEST_REVS, NAMESPACE, FQNAME
from MoinMoin.constants.namespaces import NAMESPACES_IDENTIFIER
from MoinMoin.i18n import _, L_, N_
from MoinMoin.util.forms import FileStorage
from MoinMoin.storage.middleware.validation import uuid_validator

COLS = 60
ROWS = 10


class Enum(BaseEnum):
    """
    An Enum with a convenience class method out_of.
    """
    @classmethod
    def out_of(cls, choice_specs, sort_by=None):
        """
        A convenience class method to build Enum with extra data attached to
        each valid value.

        :param choice_specs: An iterable of tuples. The elements are collected
                             into the choice_specs property; the tuples' first
                             elements become the valid values of the Enum. e.g.
                             for choice_specs = [(v1, ...), (v2, ...), ... ],
                             the valid values are v1, v2, ...

        :param sort_by: If not None, sort choice_specs by the sort_by'th
                        element.
        """
        if sort_by is not None:
            choice_specs = sorted(choice_specs, key=itemgetter(sort_by))
        else:
            choice_specs = list(choice_specs)
        return cls.valued(*[e[0] for e in choice_specs]).with_properties(choice_specs=choice_specs)


Text = String.with_properties(widget=WIDGET_TEXT)

MultilineText = String.with_properties(widget=WIDGET_MULTILINE_TEXT)

OptionalText = Text.using(optional=True)

RequiredText = Text.validated_by(Present())

OptionalMultilineText = MultilineText.using(optional=True)

RequiredMultilineText = MultilineText.validated_by(Present())


class NameNotValidError(ValueError):
    """
    The name is not valid.
    """


def validate_name(meta, itemid):
    """
    Check whether the names are valid.
    Will just return, if they are valid, will raise a NameNotValidError if not.
    """
    names = meta.get(NAME)
    current_namespace = meta.get(NAMESPACE)
    if current_namespace is None:
        raise NameNotValidError(L_("No namespace field in the meta."))
    namespaces = [namespace.rstrip('/') for namespace, _ in app.cfg.namespace_mapping]

    if len(names) != len(set(names)):
        raise NameNotValidError(L_("The names in the name list must be unique."))
    # Item names must not start with '@' or '+', '@something' denotes a field where as '+something' denotes a view.
    invalid_names = [name for name in names if name.startswith(('@', '+'))]
    if invalid_names:
        raise NameNotValidError(L_("Item names (%(invalid_names)s) must not start with '@' or '+'", invalid_names=", ".join(invalid_names)))

    namespaces = namespaces + NAMESPACES_IDENTIFIER  # Also dont allow item names to match with identifier namespaces.
    # Item names must not match with existing namespaces.
    invalid_names = [name for name in names if name.split('/', 1)[0] in namespaces]
    if invalid_names:
        raise NameNotValidError(L_("Item names (%(invalid_names)s) must not match with existing namespaces.", invalid_names=", ".join(invalid_names)))
    query = And([Or([Term(NAME, name) for name in names]), Term(NAMESPACE, current_namespace)])
    # There should be not item existing with the same name.
    if itemid is not None:
        query = And([query, Not(Term(ITEMID, itemid))])  # search for items except the current item.
    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        results = searcher.search(query)
        duplicate_names = {name for result in results for name in result[NAME] if name in names}
        if duplicate_names:
            raise NameNotValidError(L_("Item(s) named %(duplicate_names)s already exist.", duplicate_names=", ".join(duplicate_names)))


class ValidName(Validator):
    """Validator for Name
    """
    invalid_name_msg = ""

    def validate(self, element, state):
        # Make sure that the other meta is valid before validating the name.
        # TODO Change/Make sure that the below statement holds good.
        try:
            if not element.parent.parent['extra_meta_text'].valid:
                return False
        except AttributeError:
            pass
        try:
            validate_name(state['meta'], state[ITEMID])
        except NameNotValidError as e:
            self.invalid_name_msg = _(e)
            return self.note_error(element, state, 'invalid_name_msg')
        return True


class ValidJSON(Validator):
    """Validator for JSON
    """
    invalid_json_msg = L_('Invalid JSON.')
    invalid_itemid_msg = L_('Itemid not a proper UUID')
    invalid_namespace_msg = ''

    def validitemid(self, itemid):
        if not itemid:
            self.invalid_itemid_msg = L_("No ITEMID field")
            return False
        return uuid_validator(String(itemid), None)

    def validnamespace(self, current_namespace):
        if current_namespace is None:
            self.invalid_namespace_msg = L_("No namespace field in the meta.")
            return False
        namespaces = [namespace.rstrip('/') for namespace, _ in app.cfg.namespace_mapping]
        if current_namespace not in namespaces:  # current_namespace must be an existing namespace.
            self.invalid_namespace_msg = L_("%(_namespace)s is not a valid namespace.", _namespace=current_namespace)
            return False
        return True

    def validate(self, element, state):
        try:
            meta = json.loads(element.value)
        except:  # catch ANY exception that happens due to unserializing
            return self.note_error(element, state, 'invalid_json_msg')
        if not self.validnamespace(meta.get(NAMESPACE)):
            return self.note_error(element, state, 'invalid_namespace_msg')
        if state[FQNAME].field == ITEMID:
            if not self.validitemid(meta.get(ITEMID, state[FQNAME].value)):
                return self.note_error(element, state, 'invalid_itemid_msg')
        return True

JSON = OptionalMultilineText.with_properties(lang='en', dir='ltr').validated_by(ValidJSON())

URL = String.with_properties(widget=WIDGET_TEXT).validated_by(URLValidator())

OpenID = URL.using(label=L_('OpenID')).with_properties(placeholder=L_("OpenID address"))

YourOpenID = OpenID.with_properties(placeholder=L_("Your OpenID address"))

Email = String.using(label=L_('E-Mail')).with_properties(widget=WIDGET_EMAIL,
                                                         placeholder=L_("E-Mail address")).validated_by(IsEmail())

YourEmail = Email.with_properties(placeholder=L_("Your E-Mail address"))

Password = Text.with_properties(widget=WIDGET_PASSWORD).using(label=L_('Password'))

RequiredPassword = Password.validated_by(Present())

Checkbox = Boolean.with_properties(widget=WIDGET_CHECKBOX).using(optional=True, default=1)

InlineCheckbox = Checkbox.with_properties(widget=WIDGET_INLINE_CHECKBOX)

Select = Enum.with_properties(widget=WIDGET_SELECT)

# SelectSubmit is like Select in that it is rendered as a group of controls
# with different (predefined) `value`s for the same `name`. But the controls are
# submit buttons instead of radio buttons.
#
# This is used to present the user several "OK" buttons with slightly different
# semantics, like "Update" and "Update and Close" on a ticket page, or
# "Save as Draft" and "Publish" when editing a blog entry.
SelectSubmit = Enum.with_properties(widget=WIDGET_SELECT_SUBMIT)


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


class SubscriptionsJoinedString(JoinedString):
    """ A JoinedString that offers the list of children as value property and also
    appends the name of the item to the end of ITEMID subscriptions.
    """
    @property
    def value(self):
        subscriptions = []
        for child in self:
            if child.value.startswith(ITEMID):
                value = re.sub(r"\(.*\)", "", child.value)
            else:
                value = child.value
            subscriptions.append(value)
        return subscriptions

    @property
    def u(self):
        subscriptions = []
        for child in self:
            if child.u.startswith(ITEMID):
                value = re.sub(r"\(.*\)", "", child.u)
                item = flaskg.storage.document(**{ITEMID: value.split(":")[1]})
                try:
                    name_ = item.meta['name'][0]
                except IndexError:
                    name_ = "This item doesn't exist"
                value = u"{0} ({1})".format(value, name_)
            else:
                value = child.u
            subscriptions.append(value)
        return self.separator.join(subscriptions)


Tags = MyJoinedString.of(String).with_properties(widget=WIDGET_TEXT).using(
    label=L_('Tags'), optional=True, separator=', ', separator_regex=re.compile(r'\s*,\s*'))

Names = MyJoinedString.of(String).with_properties(widget=WIDGET_TEXT).using(
    label=L_('Names'), optional=True, separator=', ', separator_regex=re.compile(r'\s*,\s*')).validated_by(ValidName())

Subscriptions = SubscriptionsJoinedString.of(String).with_properties(
    widget=WIDGET_MULTILINE_TEXT, rows=ROWS, cols=COLS).using(
    label=L_('Subscriptions'), optional=True, separator='\n',
    separator_regex=re.compile(r'[\r\n]+'))

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

DateTime = (DateTimeUNIX.with_properties(widget=WIDGET_DATETIME,
                                         placeholder=_("YYYY-MM-DD HH:MM:SS (example: 2013-12-31 23:59:59)"))
            .validated_by(Converted(incorrect=L_("Please use the following format: YYYY-MM-DD HH:MM:SS"))))

File = FileStorage.with_properties(widget=WIDGET_FILE)

Hidden = String.using(optional=True).with_properties(widget=WIDGET_HIDDEN)

# optional=True is needed to get rid of the "required field" indicator on the UI (usually an asterisk)
ReadonlyStringList = List.of(String).using(optional=True).with_properties(widget=WIDGET_READONLY_STRING_LIST)

ReadonlyItemLinkList = ReadonlyStringList.with_properties(widget=WIDGET_READONLY_ITEM_LINK_LIST)


# XXX When some user chooses a Reference candidate that is removed before the
# user POSTs, the validator fails. This can be confusing.
class ValidReference(Validator):
    """
    Validator for Reference
    """
    invalid_reference_msg = L_('Invalid Reference.')

    def validate(self, element, state):
        if element.value not in element.valid_values:
            return self.note_error(element, state, 'invalid_reference_msg')
        return True


class Reference(Select.with_properties(empty_label=L_(u'(None)')).validated_by(ValidReference())):
    """
    A metadata property that points to another item selected out of the
    Results of a search query.
    """
    @class_cloner
    def to(cls, query, query_args={}):
        cls._query = query
        cls._query_args = query_args
        return cls

    @classmethod
    def _get_choice_specs(cls):
        revs = flaskg.storage.search(cls._query, **cls._query_args)
        label_getter = cls.properties['label_getter']
        choices = [(rev.meta[ITEMID], label_getter(rev)) for rev in revs]
        if cls.optional:
            choices.append((u'', cls.properties['empty_label']))
        return choices

    def __init__(self, value=Unspecified, **kw):
        super(Reference, self).__init__(value, **kw)
        # NOTE There is a slight chance of two instances of the same Reference
        # subclass having different set of choices when the storage changes
        # between their initialization.
        choice_specs = self._get_choice_specs()
        self.properties['choice_specs'] = choice_specs
        self.valid_values = [id_ for id_, name in choice_specs]


class BackReference(ReadonlyItemLinkList):
    """
    Back references built from Whoosh query.
    """
    def set(self, query, **query_args):
        revs = flaskg.storage.search(query, **query_args)
        super(BackReference, self).set([rev.meta[NAME] for rev in revs])


MultiSelect = Array.with_properties(widget=WIDGET_MULTI_SELECT)
