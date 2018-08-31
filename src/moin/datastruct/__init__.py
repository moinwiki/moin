# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - datastruct (groups and dicts) support.
"""


from moin.datastruct.backends.wiki_dicts import WikiDicts
from moin.datastruct.backends.config_dicts import ConfigDicts
from moin.datastruct.backends.composite_dicts import CompositeDicts

from moin.datastruct.backends.wiki_groups import WikiGroups
from moin.datastruct.backends.config_groups import ConfigGroups
from moin.datastruct.backends.composite_groups import CompositeGroups

from moin.datastruct.backends import GroupDoesNotExistError
from moin.datastruct.backends import DictDoesNotExistError
