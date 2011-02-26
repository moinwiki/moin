"""
    MoinMoin - signals

    We define all signals here to avoid typos/conflicts in the signal name.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from blinker import Namespace, ANY

_signals = Namespace()

item_displayed = _signals.signal('item_displayed')
item_modified = _signals.signal('item_modified')

