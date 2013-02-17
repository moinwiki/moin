# -*- coding: utf-8 -*-
"""
MoinMoin Wiki - Configuration

Developers can use this configuration to run moin right from their mercurial workdir.
"""

import os

from MoinMoin.config.default import DefaultConfig
from MoinMoin.storage import create_simple_mapping
from MoinMoin.util.interwiki import InterWikiMap


class Config(DefaultConfig):
    # Directory containing THIS wikiconfig:
    wikiconfig_dir = os.path.abspath(os.path.dirname(__file__))
    # We assume this structure for a simple "unpack and run" scenario:
    # wikiconfig.py
    # wiki/
    #      data/
    #      index/
    # contrib/
    #      interwiki/
    #          intermap.txt
    # If that's not true, feel free to adjust the pathes.
    instance_dir = os.path.join(wikiconfig_dir, 'wiki')
    data_dir = os.path.join(instance_dir, 'data')  # Note: this used to have a trailing / in the past
    index_storage = 'FileStorage', (os.path.join(instance_dir, "index"), ), {}

    # This provides a simple default setup for your backend configuration.
    # 'stores:fs:...' indicates that you want to use the filesystem backend.
    # Alternatively you can set up the mapping yourself (see HelpOnStorageConfiguration).
    namespace_mapping, backend_mapping, acl_mapping = create_simple_mapping(
        uri='stores:fs:{0}/%(backend)s/%(kind)s'.format(data_dir),
        # XXX we use rather relaxed ACLs for the development wiki:
        content_acl=dict(before=u'',
                         default=u'All:read,write,create,destroy,admin',
                         after=u'',
                         hierarchic=False, ),
        user_profile_acl=dict(before=u'',
                              default=u'All:read,write,create,destroy,admin',
                              after=u'',
                              hierarchic=False, ),
    )

    #item_root = u'Home' # front page

    # for display purposes:
    sitename = u'My MoinMoin'
    # it is required that you set this to a unique, stable and non-empty name:
    interwikiname = u'MyMoinMoin'
    # Load the interwiki map from intermap.txt:
    interwiki_map = InterWikiMap.from_file(os.path.join(wikiconfig_dir, 'contrib', 'interwiki', 'intermap.txt')).iwmap
    # we must add entries for 'Self' and our interwikiname:
    interwiki_map[interwikiname] = 'http://127.0.0.1:8080/'
    interwiki_map['Self'] = 'http://127.0.0.1:8080/'

    # setup static files' serving:
    serve_files = dict(
        docs=os.path.join(wikiconfig_dir, 'docs', '_build', 'html'),  # html docs made by sphinx
    )
    # see https://bitbucket.org/thomaswaldmann/xstatic for infos about xstatic:
    from xstatic.main import XStatic
    # names below must be package names
    mod_names = [
        'jquery', 'jquery_file_upload',
        'json_js',
        'ckeditor',
        'svgweb',
        'svgedit_moin', 'twikidraw_moin', 'anywikidraw',
    ]
    pkg = __import__('xstatic.pkg', fromlist=mod_names)
    for mod_name in mod_names:
        mod = getattr(pkg, mod_name)
        xs = XStatic(mod, root_url='/static', provider='local', protocol='http')
        serve_files.update([(xs.name, xs.base_dir)])


MOINCFG = Config  # Flask only likes uppercase stuff
# Flask settings - see the flask documentation about their meaning
SECRET_KEY = 'you need to change this so it is really secret'
#DEBUG = False # use True for development only, not for public sites!
#TESTING = False
#SESSION_COOKIE_NAME = 'session'
#PERMANENT_SESSION_LIFETIME = timedelta(days=31)
#USE_X_SENDFILE = False
#LOGGER_NAME = 'MoinMoin'
#config for flask-cache:
#CACHE_TYPE = 'filesystem'
#CACHE_DIR = '/path/to/flask-cache-dir'

# DEVELOPERS! Do not add your configuration items here - you could accidentally
# commit them! Instead, create a wikiconfig_local.py file containing this:
#
#from wikiconfig_editme import *
#
# In wikiconfig_editme.py (the indirection is needed so that the auto reload
# mechanism of the builtin server works) you do this:
#
#from wikiconfig import *
#
#class LocalConfig(Config):
#    configuration_item_1 = 'value1'
#
#MOINCFG = LocalConfig
#DEBUG = True
