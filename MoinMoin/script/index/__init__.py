# Copyright: 2006 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Fullsearch Index Script Package

    TODO: rename this module back to xapian when script framework is
    fixed to not confuse it with the xapian.org "xapian" module.
"""


from MoinMoin.util import pysupport

# create a list of extension scripts from the subpackage directory
index_scripts = pysupport.getPackageModules(__file__)
modules = index_scripts

