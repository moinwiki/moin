# Copyright: 2006 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Maintenance Script Package
"""


from MoinMoin.util import pysupport

# create a list of extension scripts from the subpackage directory
maint_scripts = pysupport.getPackageModules(__file__)
modules = maint_scripts

