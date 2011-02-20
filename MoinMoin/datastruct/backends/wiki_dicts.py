# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - WikiDict functions.

    @copyright: 2003-2007 MoinMoin:ThomasWaldmann,
                2003 by Gustavo Niemeyer,
                2009 MoinMoin:DmitrijsMilajevs,
                2010 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

from flask import flaskg
from MoinMoin.items import SOMEDICT
from MoinMoin.datastruct.backends import BaseDict, BaseDictsBackend, DictDoesNotExistError


class WikiDict(BaseDict):
    """
    Mapping of keys to values from meta of an item.

    """

    def _load_dict(self):
        dict_name = self.name
        if flaskg.unprotected_storage.has_item(dict_name):
            item = flaskg.unprotected_storage.get_item(dict_name)
            rev = item.get_revision(-1)
            somedict = rev.get(SOMEDICT, {})
            return somedict
        else:
            raise DictDoesNotExistError(dict_name)


class WikiDicts(BaseDictsBackend):

    def __contains__(self, dict_name):
        return self.is_dict_name(dict_name) and flaskg.unprotected_storage.has_item(dict_name)

    def __getitem__(self, dict_name):
        return WikiDict(name=dict_name, backend=self)

    def _retrieve_items(self, dict_name):
        item = flaskg.unprotected_storage.get_item(dict_name)
        rev = item.get_revision(-1)
        somedict = rev.get(SOMEDICT, {})
        return somedict

