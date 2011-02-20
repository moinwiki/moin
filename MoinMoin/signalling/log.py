# -*- coding: ascii -*-
"""
    MoinMoin - logging signal handlers

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from signals import *

from MoinMoin import log
logging = log.getLogger(__name__)


@item_displayed.connect_via(ANY)
def log_item_displayed(app, item_name):
    wiki_name = app.cfg.interwikiname
    logging.info("item %s:%s displayed" % (wiki_name, item_name))

@item_modified.connect_via(ANY)
def log_item_modified(app, item_name):
    wiki_name = app.cfg.interwikiname
    logging.info("item %s:%s modified" % (wiki_name, item_name))
