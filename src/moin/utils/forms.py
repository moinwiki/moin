# Copyright: 2010 Thomas Waldmann, Jason Kirtland, Scott Wilson
# License: see flatland license

"""
MoinMoin - form helpers for Flatland/Jinja2.
"""


from markupsafe import Markup
import werkzeug.datastructures

from flatland import AdaptationError, Scalar
from flatland.out.markup import Generator

from moin.i18n import _


def label_filter(tagname, attributes, contents, context, bind):
    """Provide a translated, generated fallback for field labels."""
    if bind is not None and not contents:
        contents = _(bind.label)
    return contents


label_filter.tags = {"label"}  # type: ignore[attr-defined]  # function attribute


def button_filter(tagname, attributes, contents, context, bind):
    """Show translated text in clickable buttons and submits."""
    if bind is None:
        return contents
    if tagname == "input":
        if "value" not in attributes and attributes.get("type") in ["submit", "reset"]:
            attributes["value"] = _(bind.default_value)
    elif tagname == "button" and not contents:
        contents = _(bind.default_value)
    return contents


button_filter.tags = {"input", "button"}  # type: ignore[attr-defined]  # function attribute


def required_filter(tagname, attributes, contents, context, bind):
    if bind is not None and not bind.optional:
        if tagname == "input":
            attributes["required"] = "required"
    return contents


required_filter.tags = {"input", "label"}  # type: ignore[attr-defined]  # function attribute


def autofocus_filter(tagname, attributes, contents, context, bind):
    if bind is not None:
        autofocus = bind.properties.get("autofocus")
        if autofocus:
            attributes["autofocus"] = "autofocus"
    return contents


autofocus_filter.tags = {"input", "textarea"}  # type: ignore[attr-defined]  # function attribute


def placeholder_filter(tagname, attributes, contents, context, bind):
    if bind is not None:
        placeholder = bind.properties.get("placeholder")
        if placeholder:
            attributes["placeholder"] = placeholder
    return contents


placeholder_filter.tags = {"input", "textarea"}  # type: ignore[attr-defined]  # function attribute


def error_filter_factory(class_="moin-error"):
    """Return an HTML-generation filter that annotates a field’s CSS class on error.

    :param class_: The CSS class to apply in case of a validation error on a
                   field. Default: 'moin-error'
    """

    def error_filter(tagname, attributes, contents, context, bind):
        if bind is not None and bind.errors:
            if "class" in attributes:
                attributes["class"] = " ".join([attributes["class"], class_])
            else:
                attributes["class"] = class_
        return contents

    error_filter.tags = {"input"}  # type: ignore[attr-defined]  # function attribute
    return error_filter


error_filter = error_filter_factory()


def make_generator():
    """Make an HTML generator."""
    return Generator(
        auto_domid=True,
        auto_for=True,
        auto_filter=True,
        markup_wrapper=Markup,
        filters=[label_filter, button_filter, error_filter, required_filter, placeholder_filter, autofocus_filter],
    )


class FileStorage(Scalar):
    """Schema element for Werkzeug FileStorage instances."""

    def adapt(self, value):
        if not isinstance(value, (type(None), werkzeug.datastructures.FileStorage)):
            raise AdaptationError
        return value
