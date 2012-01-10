# Copyright: 2010 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Tickets

    Tickets are usually used in forms to make sure that form submissions
    are in response to a form the same user got from moin.
"""


import time
import hmac, hashlib

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app
from flask import g as flaskg


def createTicket(tm=None, **kw):
    """ Create a ticket using a configured secret

        :param tm: unix timestamp (optional, uses current time if not given)
        :param kw: key/value stuff put into ticket, must be same for ticket
                   creation and ticket check
    """
    if tm is None:
        # for age-check of ticket
        tm = "{0:010x}".format(int(time.time()))

    kw['uid'] = flaskg.user.valid and flaskg.user.itemid or ''

    hmac_data = []
    for value in sorted(kw.items()):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif not isinstance(value, str):
            value = str(value)
        hmac_data.append(value)

    h = hmac.new(app.cfg.secrets['security/ticket'],
                 ''.join(hmac_data), digestmod=hashlib.sha1)
    return "{0}.{1}".format(tm, h.hexdigest())


def checkTicket(ticket, **kw):
    """ Check validity of a previously created ticket.

        :param ticket: a str as created by createTicket
        :param kw: see createTicket kw
    """
    try:
        timestamp_str = ticket.split('.')[0]
        timestamp = int(timestamp_str, 16)
    except ValueError:
        logging.debug("checkTicket: invalid or empty ticket {0!r}".format(ticket))
        return False
    now = time.time()
    if timestamp < now - 10 * 3600:
        logging.debug("checkTicket: too old ticket, timestamp {0!r}".format(timestamp))
        return False
    ourticket = createTicket(timestamp_str, **kw)
    logging.debug("checkTicket: returning {0!r}, got {1!r}, expected {2!r}".format(ticket == ourticket, ticket, ourticket))
    return ticket == ourticket

