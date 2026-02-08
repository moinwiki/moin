# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - new-style macros.

Macros are used to implement complex and/or dynamic page content.

These new-style macros use a class interface and always work on the internal
tree representation of the document.

TODO: Merge with converters
"""

from moin.utils import pysupport

modules = pysupport.getPackageModules(__file__)
