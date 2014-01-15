# Copyright: 2010 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.security.ticket Tests
"""


from MoinMoin.security.ticket import createTicket, checkTicket


class TestTickets(object):
    def testTickets(self):
        # value with double quotes
        ticket1 = createTicket(pagename=u'bla"bla')
        assert checkTicket(ticket1, pagename=u'bla"bla')
        # unicode value
        ticket2 = createTicket(pagename=u'\xc4rger')
        assert checkTicket(ticket2, pagename=u'\xc4rger')
        # integer value
        ticket3 = createTicket(foo=42)
        assert checkTicket(ticket3, foo=42)

        assert ticket1 != ticket2 != ticket3


coverage_modules = ['MoinMoin.security.ticket']
