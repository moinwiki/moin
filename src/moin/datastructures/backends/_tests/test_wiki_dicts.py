# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007 by MoinMoin:ThomasWaldmann
# Copyright: 2009 by MoinMoin:DmitrijsMilajevs
# Copyright: 2010 by MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.datastructures.backends.wiki_dicts tests
"""


from moin.datastructures.backends._tests import DictsBackendTest
from moin.datastructures.backends import wiki_dicts
from moin.constants.keys import WIKIDICT
from moin._tests import become_trusted, update_item

import pytest


DATA = "This is a dict item."


class TestWikiDictsBackend(DictsBackendTest):

    # Suppose that default configuration for the dicts is used which
    # is WikiDicts backend.

    @pytest.fixture(autouse=True)
    def custom_setup(self):
        become_trusted()

        wikidict = {"First": "first item", "text with spaces": "second item", "Empty string": "", "Last": "last item"}
        update_item("SomeTestDict", {WIKIDICT: wikidict}, DATA)

        wikidict = {"One": "1", "Two": "2"}
        update_item("SomeOtherTestDict", {WIKIDICT: wikidict}, DATA)

    def test__retrieve_items(self):
        wikidict_obj = wiki_dicts.WikiDicts()
        result = wiki_dicts.WikiDicts._retrieve_items(wikidict_obj, "SomeOtherTestDict")
        expected = {"Two": "2", "One": "1"}
        assert result == expected


coverage_modules = ["moin.datastructures.backends.wiki_dicts"]
