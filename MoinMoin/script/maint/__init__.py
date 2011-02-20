# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Maintenance Script Package

    @copyright: 2006 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import pysupport

# create a list of extension scripts from the subpackage directory
maint_scripts = pysupport.getPackageModules(__file__)
modules = maint_scripts

