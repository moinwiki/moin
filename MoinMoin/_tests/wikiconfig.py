# Copyright: 2000-2004 by Juergen Hermann <jh@web.de>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - test wiki configuration

Do not change any values without good reason.

We mostly want to have default values here, except for stuff that doesn't
work without setting them (like data_dir).
"""


import os
from os.path import abspath, dirname, join
from MoinMoin.config.default import DefaultConfig

class Config(DefaultConfig):
    _here = abspath(dirname(__file__))
    _root = abspath(join(_here, '..', '..'))
    data_dir = join(_here, 'wiki', 'data') # needed for plugins package TODO
    index_dir = join(_here, 'wiki', 'index')
    index_dir_tmp = join(_here, 'wiki', 'index_tmp')
    _test_items_xml = join(_here, 'testitems.xml')
    content_acl = None
    item_root = 'FrontPage'
    interwikiname = u'MoinTest'
    interwiki_map = dict(Self='http://localhost:8080/', MoinMoin='http://moinmo.in/')
    interwiki_map[interwikiname] = 'http://localhost:8080/'

