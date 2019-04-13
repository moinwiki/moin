# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - mod_wsgi driver script

    To use this, add these statements to your Apache's VirtualHost definition (omit
    WSGIDaemonProcess and WSGIProcessGroup on Windows):

    # invoke your moin wiki at the root url, like http://servername/ItemName:
    WSGIScriptAlias / /some/path/moin.wsgi
    # create some wsgi daemons - use someuser.somegroup same as your data_dir:
     moin-wsgi user=someuser group=somegroup processes=5 threads=10 maximum-requests=1000 umask=0007
    # use the daemons we defined above to process requests!
    WSGIProcessGroup moin-wsgi

    @copyright: 2010 by MoinMoin:ThomasWaldmann
    @copyright: 2016 by MoinMoin:RogerHaase
    @license: GNU GPL, see COPYING for details.
"""

import sys, os, site

# UPDATE THIS FOLLOWING LINE
moin_dir = '/path/to/moin/dir/where/wikiconfig.py/is/located'

# per http://code.google.com/p/modwsgi/wiki/VirtualEnvironments
if sys.platform == 'win32':
    site.addsitedir(moin_dir + '-venv-python/Lib/site-packages')
else:
    site.addsitedir(moin_dir + '-venv-python/lib/python2.7/site-packages')

# make sure this directory is in sys.path (.lower() avoids duplicate entries on Windows)
if not (moin_dir in sys.path or moin_dir.lower() in sys.path):
    sys.path.insert(0, moin_dir)

# for debugging sys.path issues, comment out after things are working
print '== moin2.wsgi sys.path =='
for p in sys.path:
    print p
print '== end moin2.wsgi sys.path =='

wiki_config = moin_dir + '/wikiconfig_local.py'
if not os.path.exists(wiki_config):
    wiki_config = moin_dir + '/wikiconfig.py'
print '== wiki_config path =', wiki_config, '=='

# create the Moin (Flask) WSGI application
from moin.app import create_app
application = create_app(wiki_config)

# please note: if you want to do some wsgi app wrapping, do it like shown below:
# application.wsgi_app = somewrapper(application.wsgi_app)
