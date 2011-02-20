# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.datastruct.backends.wiki_dicts tests

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>,
                2007 by MoinMoin:ThomasWaldmann,
                2009 by MoinMoin:DmitrijsMilajevs,
                2010 by MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.datastruct.backends._tests import DictsBackendTest
from MoinMoin.datastruct.backends import wiki_dicts
from MoinMoin.items import SOMEDICT
from MoinMoin._tests import become_trusted, update_item

DATA = "This is a dict item."


class TestWikiDictsBackend(DictsBackendTest):

    # Suppose that default configuration for the dicts is used which
    # is WikiDicts backend.

    def setup_method(self, method):
        become_trusted()

        somedict = {u"First": u"first item",
                    u"text with spaces": u"second item",
                    u'Empty string': u'',
                    u"Last": u"last item"}
        update_item(u'SomeTestDict', 0, {SOMEDICT: somedict}, DATA)

        somedict = {u"One": u"1",
                    u"Two": u"2"}
        update_item(u'SomeOtherTestDict', 0, {SOMEDICT: somedict}, DATA)


coverage_modules = ['MoinMoin.datastruct.backends.wiki_dicts']

