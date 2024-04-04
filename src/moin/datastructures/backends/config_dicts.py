# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - config dict backend

The config group backend enables you to define dicts in a configuration file.
"""


from moin.datastructures.backends import BaseDict, BaseDictsBackend, DictDoesNotExistError


class ConfigDict(BaseDict):
    pass


class ConfigDicts(BaseDictsBackend):

    def __init__(self, dicts):
        super().__init__()

        self._dicts = dicts

    def __contains__(self, dict_name):
        return self.is_dict_name(dict_name) and dict_name in self._dicts

    def __iter__(self):
        return iter(self._dicts.keys())

    def __getitem__(self, dict_name):
        return ConfigDict(name=dict_name, backend=self)

    def _retrieve_items(self, dict_name):
        try:
            return self._dicts[dict_name]
        except KeyError:
            raise DictDoesNotExistError(dict_name)
