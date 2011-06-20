# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007 by MoinMoin:ThomasWaldmann
# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# Copyright: 2010 by MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.datastruct.backends.wiki_dicts tests
"""


from MoinMoin.datastruct.backends._tests import DictsBackendTest
from MoinMoin.datastruct.backends import wiki_dicts
from MoinMoin.config import SOMEDICT
from MoinMoin._tests import become_trusted, update_item
from MoinMoin.conftest import init_test_app, deinit_test_app
from MoinMoin._tests import wikiconfig
DATA = "This is a dict item."


class TestWikiDictsBackend(DictsBackendTest):

    # Suppose that default configuration for the dicts is used which
    # is WikiDicts backend.

    def setup_method(self, method):
        # temporary hack till we apply test cleanup mechanism on tests.
        init_test_app(wikiconfig.Config)
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

