#!/usr/bin/python
# Copyright: 2013 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MakeMoinMenu.py - create a tiny script that provides a menu making it easy to run common moin2 admin tasks.
Then run quickinstall process to create a virtual env and install required packages.
"""

import os
import sys

import MoinMoin  # validate python version
from m import help, Menu

# run the script from the hosts main Python 2.7 installation, the virtual env may not exist
if os.name == 'nt':
    with open('m.bat', 'w') as f:
        f.write('@{} m.py %*\n'.format(sys.executable))
else:
    with open('m', 'w') as f:
        f.write('{} m.py $*\n'.format(sys.executable))
        os.fchmod(f.fileno(), 0775)
# run quickinstall to create or refresh the virtual env using the menu process
menu = Menu()
choice = getattr(menu, 'cmd_quickinstall')
choice(*sys.argv[1:])  # <override-path-to-venv> --download_cache <override-path-to-cache>
# give user a hint as to what to do next
if os.name == 'nt':
    print '\n> > > Type "m" for menu < < <'
else:
    print '\n> > > Type "./m" for menu < < <'
