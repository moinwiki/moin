# Copyright: 2010 MoinMoin:ValentinJaniaut
# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Smiley converter

Replace all the text corresponding to a smiley, by the corresponding
element for the DOM Tree.
"""

import re

from emeraldtree import ElementTree as ET

from moin.utils.mime import type_moin_document
from moin.utils.tree import moin_page

from . import default_registry


class Converter:
    """
    Replace each smiley by the corresponding element in the DOM Tree
    """

    smileys = {
        # markup: smiley name
        "X-(": "angry",
        ":D": "biggrin",
        "<:(": "frown",
        ":o": "redface",
        ":(": "sad",
        ":)": "smile",
        "B)": "smile2",
        ":))": "smile3",
        ";)": "smile4",
        "/!\\": "alert",
        "<!>": "attention",
        "(!)": "idea",
        ":-?": "tongue",
        ":\\": "ohwell",
        ">:>": "devil",
        "|)": "tired",
        ":-(": "sad",
        ":-)": "smile",
        "B-)": "smile2",
        ":-))": "smile3",
        ";-)": "smile4",
        "|-)": "tired",
        "(./)": "checkmark",
        "{OK}": "thumbs-up",
        "{X}": "icon-error",
        "{i}": "icon-info",
        "{1}": "prio1",
        "{2}": "prio2",
        "{3}": "prio3",
        "{*}": "star_on",
        "{o}": "star_off",
    }

    smiley_rule = r"""
    (^|(?<=\s))  # we require either beginning of line or some space before a smiley
    (%(smiley)s)  # one of the smileys
    ($|(?=\s))  # we require either ending of line or some space after a smiley
""" % {
        "smiley": "|".join([re.escape(s) for s in smileys])
    }

    smiley_re = re.compile(smiley_rule, re.UNICODE | re.VERBOSE)

    # We do not process any smiley conversion within these elements.
    tags_to_ignore = {"code", "blockcode", "nowiki"}

    @classmethod
    def _factory(cls, input, output, icon=None, **kw):
        if icon == "smiley":
            return cls()

    def __call__(self, content):
        self.do_children(content)
        return content

    def do_children(self, element):
        # We store the new children of the element in this list
        new_children = []

        # If we do not want smiley conversion for the children of
        # a specific element, we do not process the conversion.
        if element.tag.name in self.tags_to_ignore:
            return element
        for child in element:
            if isinstance(child, ET.Element):
                # We have an ET.Element, so we continue the recursion
                children = self.do_children(child)
                if children is None:
                    children = ()
                elif not isinstance(children, (list, tuple)):
                    children = (children,)
                new_children.extend(children)
            else:
                # Otherwise, we have a text node, so we convert the smileys
                new_children.extend(self.do_smiley(child))

        if new_children:
            # We remove all the old children of the element
            element.remove_all()
            # And we replace it by the new one
            element.extend(new_children)
        return element

    def do_smiley(self, element):
        """
        From a text, return a list with smileys replaced
        by the appropriate elements, and the former text for the
        other elements of the list.
        """
        # We split our string into different items arround
        # the matched smiley.
        splitted_string = re.split(self.smiley_re, element)
        # And then for each item of the list,
        # if it is a smiley, we replace it by the appropriate element
        return [self.replace_smiley(item) for item in splitted_string]

    def replace_smiley(self, text):
        """
        Replace a given string by the appropriate
        element if the string is exactly a smiley.
        Otherwise return the string without any change.
        """
        # Remove the space of the smiley_text if any
        smiley_markup = text.strip()

        if smiley_markup in self.smileys:
            smiley_name = self.smileys[smiley_markup]
            attrib = {moin_page("class"): "moin-text-icon moin-" + smiley_name}
            return ET.Element(moin_page.span, attrib=attrib, children=[smiley_markup])
        else:
            # if the text was not a smiley, just return the markup without any transformations
            return text


default_registry.register(Converter._factory, type_moin_document, type_moin_document)
