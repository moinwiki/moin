# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - User Accounts Script Package

    @copyright: 2006 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import pysupport

# create a list of extension scripts from the subpackage directory
account_scripts = pysupport.getPackageModules(__file__)
modules = account_scripts

