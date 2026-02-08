# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - signals

Define all signals here to avoid typos/conflicts in signal names.
"""

from blinker import Namespace, ANY  # noqa

_signals = Namespace()

item_displayed = _signals.signal("item_displayed")
item_modified = _signals.signal("item_modified")
