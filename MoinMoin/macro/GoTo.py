# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - GoTo macro

Provides a goto box.
"""


from emeraldtree import ElementTree as ET

from MoinMoin.i18n import _, L_, N_
from MoinMoin.macro._base import MacroBlockBase
from MoinMoin.util.tree import html

class Macro(MacroBlockBase):
    def macro(self):
        return ET.XML("""
<form xmlns="%s" method="get" action="%s/%s">
    <input type="hidden" name="do" value="goto" />
    <p>
        <input type="text" name="target" size="30" />
        <input type="submit" value="%s" />
    </p>
</form>
""" % (html,
        self.request.getScriptname(),
        self.page_name,
        _("Go To Item"))) #HHH ?
