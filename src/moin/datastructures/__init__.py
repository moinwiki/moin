# Copyright: 2009 MoinMoin:DmitrijsMilajevs
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - datastructures (groups and dicts) support.
"""


from moin.datastructures.backends.wiki_dicts import WikiDicts
from moin.datastructures.backends.config_dicts import ConfigDicts
from moin.datastructures.backends.composite_dicts import CompositeDicts

from moin.datastructures.backends.wiki_groups import WikiGroups
from moin.datastructures.backends.config_groups import ConfigGroups
from moin.datastructures.backends.composite_groups import CompositeGroups

from moin.datastructures.backends import GroupDoesNotExistError
from moin.datastructures.backends import DictDoesNotExistError
