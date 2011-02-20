# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Fullsearch Index Script Package

    TODO: rename this module back to xapian when script framework is
    fixed to not confuse it with the xapian.org "xapian" module.

    @copyright: 2006 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import pysupport

# create a list of extension scripts from the subpackage directory
index_scripts = pysupport.getPackageModules(__file__)
modules = index_scripts

