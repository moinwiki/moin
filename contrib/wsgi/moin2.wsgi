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

this_dir = os.path.dirname(os.path.abspath(__file__))

# per http://code.google.com/p/modwsgi/wiki/VirtualEnvironments
if sys.platform == 'win32':
    site.addsitedir(this_dir + '-venv-python/Lib/site-packages')
else:
    site.addsitedir(this_dir + '-venv-python2.7/lib/python2.7/site-packages')

# make sure this directory is in sys.path (.lower() avoids duplicate entries on Windows)
if not (this_dir in sys.path or this_dir.lower() in sys.path):
    sys.path.insert(0, this_dir)

# write to error.log for debugging sys.path issues
print '== moin2.wsgi sys.path =='
for p in sys.path:
    print p
print '== end moin2.wsgi sys.path =='

wiki_config = this_dir + '/wikiconfig_local.py'
if not os.path.exists(wiki_config):
    wiki_config = this_dir + '/wikiconfig.py'
print '== wiki_config path =', wiki_config, '=='

# application is the Flask application
from moin.app import create_app
application = create_app(wiki_config)

# please note: if you want to do some wsgi app wrapping, do it like shown below:
# application.wsgi_app = somewrapper(application.wsgi_app)
