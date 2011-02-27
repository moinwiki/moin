"""
MoinMoin - test wiki configuration

Do not change any values without good reason.

We mostly want to have default values here, except for stuff that doesn't
work without setting them (like data_dir).

@copyright: 2000-2004 by Juergen Hermann <jh@web.de>
@license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import os
from os.path import abspath, dirname, join
from MoinMoin.config.default import DefaultConfig

class Config(DefaultConfig):
    _here = abspath(dirname(__file__))
    _root = abspath(join(_here, '..', '..'))
    data_dir = join(_here, 'wiki', 'data') # needed for plugins package TODO
    _test_items_xml = join(_here, 'testitems.xml')
    content_acl = None
    item_root = 'FrontPage'

