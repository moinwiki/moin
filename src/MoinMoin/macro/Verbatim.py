# Copyright: 2005-2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Output the input text as is: <<Verbatim(return `same` __text__ '''as''' entered)>>
"""


from MoinMoin.macro._base import MacroInlineBase


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        return arguments[0]
