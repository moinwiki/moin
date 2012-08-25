# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - itemtype related constants
"""


from __future__ import absolute_import, division

from collections import namedtuple

from MoinMoin.i18n import L_


ItemtypeSpec = namedtuple('ItemtypeSpec', 'itemtype display_name description')

ITEMTYPE_DEFAULT = u'default'
ITEMTYPE_TICKET = u'ticket'
ITEMTYPE_BLOG = u'blog'
ITEMTYPE_BLOGENTRY = u'blogentry'

# TODO Perhaps construct this list from the item_registry instead of having it
# as a constant, which is more extensible (we can have itemtype plugins in
# future and plugged-in itemtypes will be included too). Two more fields (ie.
# display name and description) are needed in the registry then to support the
# automatic construction.
ITEMTYPES = [
    ItemtypeSpec(ITEMTYPE_DEFAULT, L_('Default'), L_('Wiki item')),
    ItemtypeSpec(ITEMTYPE_TICKET, L_('Ticket'), L_('Ticket item')),
    ItemtypeSpec(ITEMTYPE_BLOG, L_('Blog'), L_('Blog item')),
    ItemtypeSpec(ITEMTYPE_BLOGENTRY, L_('Blog entry'), L_('Blog entry item')),
]
