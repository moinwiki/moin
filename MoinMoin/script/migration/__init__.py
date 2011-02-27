"""
    MoinMoin - Migration Script Package

    @copyright: 2006 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from MoinMoin.util import pysupport

# create a list of extension scripts from the subpackage directory
migration_scripts = pysupport.getPackageModules(__file__)
modules = migration_scripts

