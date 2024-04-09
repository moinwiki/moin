# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - logging signal handlers
"""


from .signals import ANY, item_displayed, item_modified
from flask import got_request_exception

from .. import log

logging = log.getLogger(__name__)


@item_displayed.connect_via(ANY)
def log_item_displayed(app, fqname):
    wiki_name = app.cfg.interwikiname
    logging.info(f"item {wiki_name}:{str(fqname)} displayed")


@item_modified.connect_via(ANY)
def log_item_modified(app, fqname, **kwargs):
    wiki_name = app.cfg.interwikiname
    logging.info(f"item {wiki_name}:{str(fqname)} modified")


@got_request_exception.connect_via(ANY)
def log_exception(sender, exception, **extra):
    logging.exception(exception)
