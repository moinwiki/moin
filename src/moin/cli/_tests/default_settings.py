# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli._tests.default_settings configurations for tests

these settings will run tests against the development server started via moin.cli._tests.conftest.server
to run tests against another server, copy this file to settings.py
if it exists, settings.py needs to contain all the entries as default_settings.py"""

from moin.utils.iri import Iri

SITE_SCHEME = "http"
SITE_HOST = "127.0.0.1:9080"
SITE_WIKI_ROOT = ""  # must start with '/' if set
CRAWL_NAMESPACE = "/help-en"
CRAWL_START = Iri(scheme=SITE_SCHEME, authority=SITE_HOST, path=f"{SITE_WIKI_ROOT}{CRAWL_NAMESPACE}")
DO_CRAWL = True  # for test development, skip the crawl, load most recent crawl.csv
