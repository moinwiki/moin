# copyright: 2010 by MoinMoin:ThomasWaldmann
# copyright: 2016 by MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - mod_wsgi driver script

    To use this, copy this file to your wiki root (wikiconfig.py resides there),
    then add these statements to your Apache's VirtualHost definition
    (omit WSGIDaemonProcess and WSGIProcessGroup on Windows):

    # invoke your moin wiki at the root url, like http://servername/ItemName:
    WSGIScriptAlias / /<path-to>/moin2.wsgi
    # create some wsgi daemons - use someuser.somegroup same as your data_dir:
     moin-wsgi user=someuser group=somegroup processes=5 threads=10 maximum-requests=1000 umask=0007
    # use the daemons we defined above to process requests
    WSGIProcessGroup moin-wsgi
"""

import sys
import os
import site


moin_dir = os.path.dirname(os.path.abspath(__file__))

if sys.platform == 'win32':
    site.addsitedir(moin_dir + '-venv-python/Lib/site-packages')
else:
    site.addsitedir(moin_dir + '-venv-{0}/lib/{0}/site-packages'.format(sys.executable))

# make sure this directory is in sys.path (.lower() avoids duplicate entries on Windows)
if not (moin_dir in sys.path or moin_dir.lower() in sys.path):
    sys.path.insert(0, moin_dir)

# for debugging sys.path issues, comment out after things are working
print('== moin2.wsgi sys.path ==')
for p in sys.path:
    print(p)
print('== end moin2.wsgi sys.path ==')

wiki_config = moin_dir + '/wikiconfig_local.py'
if not os.path.exists(wiki_config):
    wiki_config = moin_dir + '/wikiconfig.py'
print('== wiki_config path =', wiki_config, '==')

# create the Moin (Flask) WSGI application
from moin.app import create_app
application = create_app(wiki_config)

# please note: if you want to do some wsgi app wrapping, do it like shown below:
# application.wsgi_app = somewrapper(application.wsgi_app)
