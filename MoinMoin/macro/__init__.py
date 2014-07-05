# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - New style macros

Macros are used to implement complex and/or dynamic page content.

These new-style macros uses a class interface and always works on the internal
tree representation of the document.

TODO: Merge with converters
"""


from MoinMoin.util import pysupport

modules = pysupport.getPackageModules(__file__)
