# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - datastruct (groups and dicts) support.
"""


from MoinMoin.datastruct.backends.wiki_dicts import WikiDicts
from MoinMoin.datastruct.backends.config_dicts import ConfigDicts
from MoinMoin.datastruct.backends.composite_dicts import CompositeDicts

from MoinMoin.datastruct.backends.wiki_groups import WikiGroups
from MoinMoin.datastruct.backends.config_groups import ConfigGroups
from MoinMoin.datastruct.backends.composite_groups import CompositeGroups

from MoinMoin.datastruct.backends import GroupDoesNotExistError
from MoinMoin.datastruct.backends import DictDoesNotExistError

