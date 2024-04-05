# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tree name and element generator
"""


from emeraldtree import ElementTree as ET


class Name(ET.QName):
    """
    Represents a QName and factory for elements with this QName
    """

    def __call__(self, attrib=None, children=(), **extra):
        return ET.Element(self, attrib=attrib, children=children, **extra)


class Namespace(str):
    """
    Represents a namespace and factory for Names within this namespace
    """

    def __call__(self, name):
        """
        Create a Name within this namespace

        :param name: The name within this namespace.
        :returns: A Name
        """
        return Name(name, self)

    def __getattr__(self, key):
        """
        Create a Name within this namespace

        The given key is used to generate a QName within the represented
        namespace.  Two modifications are applied to the key:
         - a trailing "_" (underscore) is removed and
         - all included "_" (underscore) are replaced by "-" (hyphen).

        :returns: A Name
        """
        if "_" in key:
            if key.startswith("_"):
                raise AttributeError(key)
            if key.endswith("_"):
                key = key[:-1]
            key = key.replace("_", "-")
        return Name(key, self)

    def __repr__(self):
        return f"<{self.__class__.__name__}({str(self)!r})>"

    @property
    def namespace(self):
        return self


# MoinMoin namespaces - any-converter-in => Moin DOM => any-converter-out
#
# Namespaces are used to prevent naming collisions
#    moin_page is used to define many types of elements on the moin DOM
#    xinclude is used to describe transclusions on the moin DOM
#    xlink is used to describe links on the moin DOM
#    the html_in and html_out converters use the html namespace to process file input and output
#    the html_in and mediawiki_in converters place style attributes on the moin DOM using the html namespace
#        TODO: the above may be an error, the moin_page namespace should be used
#    the docbook_in and docbook_out converters use the docbook namespace to process file input and output
#    xml is used by html_in, html_out, and markdown_in to place ID attributes on the moin DOM
#        TODO: the above may be an error, the moin_page namespace should be used
#    xml is used in several tests
#    the dc namespace is not used
#    the mathml namespace is not used
#    the svg namespace is not used

moin_page = Namespace("http://moinmo.in/namespaces/page")

# Well-known namespaces
dc = Namespace("http://purl.org/dc/elements/1.1/")
html = Namespace("http://www.w3.org/1999/xhtml")
mathml = Namespace("http://www.w3.org/1998/Math/MathML")
svg = Namespace("http://www.w3.org/2000/svg")
xinclude = Namespace("http://www.w3.org/2001/XInclude")
xlink = Namespace("http://www.w3.org/1999/xlink")
docbook = Namespace("http://docbook.org/ns/docbook")
xml = Namespace("http://www.w3.org/XML/1998/namespace")
