# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - logging signal handlers
"""


from .signals import *

from MoinMoin import log
logging = log.getLogger(__name__)


@item_displayed.connect_via(ANY)
def log_item_displayed(app, item_name):
    wiki_name = app.cfg.interwikiname
    logging.info("item {0}:{1} displayed".format(wiki_name, item_name))

@item_modified.connect_via(ANY)
def log_item_modified(app, item_name):
    wiki_name = app.cfg.interwikiname
    logging.info("item {0}:{1} modified".format(wiki_name, item_name))
