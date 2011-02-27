"""
    TemplateList - compatibility wrapper around PagenameList

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from MoinMoin.macro.PagenameList import Macro as PNLMacro

class Macro(PNLMacro):
    def macro(self, needle=u''):
        return super(Macro, self).macro(needle, regex=True)


