"""default_settings for sitetesting

these settings will run tests against the server started via run_moin.py
to run tests against another server, copy this file to settings.py
if it exists, settings.py needs to contain all the entries as default_settings.py"""

from moin.utils.iri import Iri

SITE_SCHEME = 'http'
SITE_HOST = '127.0.0.1:9080'
SITE_WIKI_ROOT = ''
CRAWL_NAMESPACE = '/help-en'
CRAWL_START = Iri(scheme=SITE_SCHEME, authority=SITE_HOST, path=f'{SITE_WIKI_ROOT}{CRAWL_NAMESPACE}')
DO_CRAWL = True  # for test development, skip the crawl, load most recent crawl.csv
