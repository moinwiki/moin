# Copyright: 2012 MoinMoin:PavelSviderski
# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Flatland widgets

    General Flatland widgets containing hints for the templates.
"""


import re
import datetime
import json
from operator import itemgetter

from flatland import (
    Form,  # noqa
    String,
    Integer,
    Boolean,
    Enum as BaseEnum,
    JoinedString,  # noqa
    List,
    Array,
    DateTime as _DateTime,
)
from flatland.util import class_cloner, Unspecified
from flatland.validation import Validator, Present, IsEmail, URLValidator, Converted, ValueAtLeast
from flatland.exc import AdaptationError

from whoosh.query import Term, Or, Not, And

from flask import g as flaskg
from flask import current_app as app
from flask import flash

from moin.constants.forms import (
    WIDGET_ANY_INTEGER,
    WIDGET_CHECKBOX,
    WIDGET_DATETIME,
    WIDGET_EMAIL,
    WIDGET_FILE,
    WIDGET_HIDDEN,
    WIDGET_INLINE_CHECKBOX,
    WIDGET_MULTILINE_TEXT,
    WIDGET_MULTI_SELECT,
    WIDGET_PASSWORD,
    WIDGET_RADIO_CHOICE,
    WIDGET_READONLY_ITEM_LINK_LIST,
    WIDGET_READONLY_STRING_LIST,
    WIDGET_SEARCH,
    WIDGET_SELECT,
    WIDGET_SELECT_SUBMIT,
    WIDGET_SMALL_NATURAL,
    WIDGET_TEXT,
)

from moin.constants.keys import ITEMID, NAME, LATEST_REVS, NAMESPACE, FQNAME
from moin.constants.namespaces import NAMESPACES_IDENTIFIER
from moin.i18n import _, L_
from moin.utils import utcfromtimestamp
from moin.utils.forms import FileStorage
from moin.storage.middleware.validation import uuid_validator

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
    Common validation code for new, renamed and reverted items.

    Will return None if valid, or raise a NameNotValidError if not.
    """
    names = meta.get(NAME)
    current_namespace = meta.get(NAMESPACE)
    if current_namespace is None:
        raise NameNotValidError(L_("No namespace field in the meta."))
    namespaces = [namespace.rstrip("/") for namespace, _ in app.cfg.namespace_mapping]

    if len(names) != len(set(names)):
        msg = L_("The names in the name list must be unique.")
        flash(msg, "error")
        raise NameNotValidError(msg)

    # Item names must not start with '@' or '+', '@something' denotes a field where as '+something' denotes a view.
    invalid_names = [name for name in names if name.startswith(("@", "+"))]
    if invalid_names:
        msg = L_("Item names ({invalid_names}) must not start with '@' or '+'").format(
            invalid_names=", ".join(invalid_names)
        )
        flash(msg, "error")
        raise NameNotValidError(msg)

    # Item names must not contain commas
    invalid_names = [name for name in names if "," in name]
    if invalid_names:
        msg = L_(
            "Item name ({invalid_names}) must not contain ',' characters. "
            "Create item with 1 name, use rename to create multiple names."
        ).format(invalid_names=", ".join(invalid_names))
        flash(msg, "error")
        raise NameNotValidError(msg)

    namespaces = namespaces + NAMESPACES_IDENTIFIER  # Also dont allow item names to match with identifier namespaces.
    # Item names must not match with existing namespaces.
    invalid_names = [name for name in names if name.split("/", 1)[0] in namespaces]
    if invalid_names:
        msg = L_("Item names ({invalid_names}) must not match with existing namespaces.").format(
            invalid_names=", ".join(invalid_names)
        )
        flash(msg, "error")  # duplicate message at top of form
        raise NameNotValidError(msg)
    query = And([Or([Term(NAME, name) for name in names]), Term(NAMESPACE, current_namespace)])
    # There should be not item existing with the same name.
    if itemid is not None:
        query = And([query, Not(Term(ITEMID, itemid))])  # search for items except the current item.
    with flaskg.storage.indexer.ix[LATEST_REVS].searcher() as searcher:
        results = searcher.search(query)
        duplicate_names = {name for result in results for name in result[NAME] if name in names}
        if duplicate_names:
            msg = L_("Item(s) named {duplicate_names} already exist.").format(
                duplicate_names=", ".join(duplicate_names)
            )
            flash(msg, "error")  # duplicate message at top of form
            raise NameNotValidError(msg)


class ValidName(Validator):
    """Validator for Name"""

    invalid_name_msg = ""

    def validate(self, element, state):
        if state is None:
            # incoming request is from +usersettings#personal;
            # apps/frontend/views.py will validate changes to user names
            return True
        try:
            validate_name(state["meta"], state[ITEMID])
        except NameNotValidError as e:
            self.invalid_name_msg = _(str(e))
            return self.note_error(element, state, "invalid_name_msg")
        return True


class ValidJSON(Validator):
    """Validator for JSON"""

    invalid_json_msg = L_("Invalid JSON.")
    invalid_itemid_msg = L_("Itemid not a proper UUID")
    invalid_namespace_msg = ""

    def validitemid(self, itemid):
        if not itemid:
            self.invalid_itemid_msg = L_("No ITEMID field")
            return False
        return uuid_validator(String(itemid), None)

    def validnamespace(self, current_namespace):
        if current_namespace is None:
            self.invalid_namespace_msg = L_("No namespace field in the meta.")
            return False
        namespaces = [namespace.rstrip("/") for namespace, _ in app.cfg.namespace_mapping]
        if current_namespace not in namespaces:  # current_namespace must be an existing namespace.
            self.invalid_namespace_msg = L_("{_namespace} is not a valid namespace.").format(
                _namespace=current_namespace
            )
            return False
        return True

    def validate(self, element, state):
        try:
            meta = json.loads(element.value)
        except:  # noqa - catch ANY exception that happens due to unserializing
            return self.note_error(element, state, "invalid_json_msg")
        if not self.validnamespace(meta.get(NAMESPACE)):
            return self.note_error(element, state, "invalid_namespace_msg")
        if state[FQNAME].field == ITEMID:
            if not self.validitemid(meta.get(ITEMID, state[FQNAME].value)):
                return self.note_error(element, state, "invalid_itemid_msg")
        return True


JSON = OptionalMultilineText.with_properties(lang="en", dir="ltr").validated_by(ValidJSON())

URL = String.with_properties(widget=WIDGET_TEXT).validated_by(URLValidator())

Email = (
    String.using(label=L_("E-Mail"))
    .with_properties(widget=WIDGET_EMAIL, placeholder=L_("E-Mail address"))
    .validated_by(IsEmail())
)

YourEmail = Email.with_properties(placeholder=L_("Your E-Mail address"))

Password = Text.with_properties(widget=WIDGET_PASSWORD).using(label=L_("Password"))

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
    """A JoinedString that offers the list of children as value property and also
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
                # itemid:67155f195938426d82502540493e8acf (creole)
                value = child.u.split(" ", 1)[0]
                item = flaskg.storage.document(**{ITEMID: value.split(":")[1]})
                try:
                    name_ = item.meta["name"][0]
                except IndexError:
                    name_ = _("This item doesn't exist.")
                except AttributeError:
                    name_ = _("This item name is corrupt, delete and recreate.")
                value = f"{value} ({name_})"
            else:
                # name::ExampleItem | tags::demo | nameprefix::jp | namere::.* | name:MyNamespace:ExampleItem
                value = child.u
            subscriptions.append(value)
        return self.separator.join(subscriptions)


Tags = (
    MyJoinedString.of(String)
    .with_properties(widget=WIDGET_TEXT)
    .using(label=L_("Tags"), optional=True, separator=", ", separator_regex=re.compile(r"\s*,\s*"))
)

Names = (
    MyJoinedString.of(String)
    .with_properties(widget=WIDGET_TEXT)
    .using(label=L_("Names"), optional=True, separator=", ", separator_regex=re.compile(r"\s*,\s*"))
    .validated_by(ValidName())
)

Subscriptions = (
    SubscriptionsJoinedString.of(String)
    .with_properties(widget=WIDGET_MULTILINE_TEXT, rows=ROWS, cols=COLS)
    .using(label=L_("Subscriptions"), optional=True, separator="\n", separator_regex=re.compile(r"[\r\n]+"))
)

Quicklinks = (
    MyJoinedString.of(String)
    .with_properties(widget=WIDGET_MULTILINE_TEXT, rows=ROWS, cols=COLS)
    .using(label=L_("Quick Links"), optional=True, separator="\n", separator_regex=re.compile(r"[\r\n]+"))
)

Search = Text.using(default="", optional=True).with_properties(widget=WIDGET_SEARCH, placeholder=L_("Search Query"))

_Integer = Integer.validated_by(Converted())

AnyInteger = _Integer.with_properties(widget=WIDGET_ANY_INTEGER)

Natural = AnyInteger.validated_by(ValueAtLeast(0))

SmallNatural = _Integer.with_properties(widget=WIDGET_SMALL_NATURAL)

RadioChoice = Text.with_properties(widget=WIDGET_RADIO_CHOICE)


class DateTimeUNIX(_DateTime):
    """
    A DateTime that uses a UNIX timestamp instead of datetime as internal
    representation of DateTime.
    """

    def serialize(self, value):
        """Serializes value to string."""
        if isinstance(value, int):
            try:
                value = utcfromtimestamp(value)
            except ValueError:
                pass
        return super().serialize(value)

    def adapt(self, value):
        """Coerces value to a native UNIX timestamp.

        If value is an instance of int and it is a correct UNIX timestamp,
        returns it unchanged. Otherwise uses DateTime superclass to parse it.
        """
        if isinstance(value, int):
            try:
                # check if a value is a correct timestamp
                dt = utcfromtimestamp(value)
                return value
            except (ValueError, OSError):  # OSError errno 75 "Value too large for defined data type"
                raise AdaptationError()
        dt = super().adapt(value)
        if isinstance(dt, datetime.datetime):
            # XXX forces circular dependency when it is in the head import block
            from moin.themes import utctimestamp

            # TODO: Add support for timezones
            dt = utctimestamp(dt)
        return dt


DateTime = DateTimeUNIX.with_properties(
    widget=WIDGET_DATETIME, placeholder=_("YYYY-MM-DD HH:MM:SS (example: 2013-12-31 23:59:59)")
).validated_by(Converted(incorrect=L_("Please use the following format: YYYY-MM-DD HH:MM:SS")))

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

    invalid_reference_msg = L_("Invalid Reference.")

    def validate(self, element, state):
        if element.value not in element.valid_values:
            return self.note_error(element, state, "invalid_reference_msg")
        return True


class Reference(Select.with_properties(empty_label=L_("(None)")).validated_by(ValidReference())):
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
        label_getter = cls.properties["label_getter"]
        choices = [(rev.meta[ITEMID], label_getter(rev)) for rev in revs]
        if cls.optional:
            choices.append(("", cls.properties["empty_label"]))
        return choices

    def __init__(self, value=Unspecified, **kw):
        super().__init__(value, **kw)
        # NOTE There is a slight chance of two instances of the same Reference
        # subclass having different set of choices when the storage changes
        # between their initialization.
        choice_specs = self._get_choice_specs()
        self.properties["choice_specs"] = choice_specs
        self.valid_values = [id_ for id_, name in choice_specs]


class BackReference(ReadonlyItemLinkList):
    """
    Back references built from Whoosh query.
    """

    def set(self, query, **query_args):
        revs = flaskg.storage.search(query, **query_args)
        super().set([rev.meta[NAME] for rev in revs])


MultiSelect = Array.with_properties(widget=WIDGET_MULTI_SELECT)
