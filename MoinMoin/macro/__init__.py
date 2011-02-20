"""
MoinMoin - New style macros

Macros are used to implement complex and/or dynamic page content.

These new-style macros uses a class interface and always works on the internal
tree representation of the document.

TODO: Merge with converters

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import pysupport

modules = pysupport.getPackageModules(__file__)
