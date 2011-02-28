# Copyright: 2006 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Migration Script Package
"""


from MoinMoin.util import pysupport

# create a list of extension scripts from the subpackage directory
migration_scripts = pysupport.getPackageModules(__file__)
modules = migration_scripts

