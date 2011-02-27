"""
MoinMoin - config dict backend

The config group backend enables you to define dicts in a configuration file.

@copyright: 2009 MoinMoin:DmitrijsMilajevs
@license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from MoinMoin.datastruct.backends import BaseDict, BaseDictsBackend, DictDoesNotExistError


class ConfigDict(BaseDict):
    pass


class ConfigDicts(BaseDictsBackend):

    def __init__(self, dicts):
        super(ConfigDicts, self).__init__()

        self._dicts = dicts

    def __contains__(self, dict_name):
        return self.is_dict_name(dict_name) and dict_name in self._dicts

    def __iter__(self):
        return self._dicts.iterkeys()

    def __getitem__(self, dict_name):
        return ConfigDict(name=dict_name, backend=self)

    def _retrieve_items(self, dict_name):
        try:
            return self._dicts[dict_name]
        except KeyError:
            raise DictDoesNotExistError(dict_name)

