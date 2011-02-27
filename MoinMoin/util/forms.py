# Copyright: 2010 Thomas Waldmann, Jason Kirtland, Scott Wilson
# License: see flatland license

"""
    MoinMoin - form helpers for flatland / jinja2
"""


from jinja2 import Markup

from flatland.out.markup import Generator
from flatland.schema.util import find_i18n_function

from MoinMoin.i18n import _, L_, N_

def label_filter(tagname, attributes, contents, context, bind):
    """Provide a translated, generated fallback for field labels."""
    if bind is not None and not contents:
        contents = _(bind.label)
    return contents
label_filter.tags = set(['label'])


def button_filter(tagname, attributes, contents, context, bind):
    """Show translated text in clickable buttons and submits."""
    if bind is None:
        return contents
    if tagname == 'input':
        if ('value' not in attributes and
            attributes.get('type') in ['submit', 'reset', ]):
            attributes['value'] = _(bind.default_value)
    elif tagname == 'button' and not contents:
        contents = _(bind.default_value)
    return contents
button_filter.tags = set(['input', 'button'])


def error_filter_factory(class_='moin-error'):
    """Returns an HTML generation filter annotating field CSS class on error.

    :param class: The css class to apply in case of validation error on a
                  field.  Default: 'error'
    """
    def error_filter(tagname, attributes, contents, context, bind):
        if bind is not None and bind.errors:
            if 'class' in attributes:
                attributes['class'] = ' '.join([attributes['class'], class_])
            else:
                attributes['class'] = class_
        return contents
    error_filter.tags = set(['input'])
    return error_filter

error_filter = error_filter_factory()


def make_generator():
    """make an html generator"""
    return Generator(auto_domid=True, auto_for=True, auto_filter=True,
                     markup_wrapper=Markup,
                     filters=[label_filter, button_filter, error_filter])

