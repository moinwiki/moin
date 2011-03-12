# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MailTo Macro displays an E-Mail address (either a valid mailto:
link for logged in users or an obfuscated display as given as the macro argument.
"""


from flask import flaskg

from MoinMoin.util.tree import moin_page, xlink
from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        # TODO new arg parsing is not compatible, splits at blanks
        try:
            email = arguments[0]
        except IndexError:
            raise ValueError("You need to give an (obfuscated) email address")

        try:
            text = arguments[1]
        except IndexError:
            text = u''

        from MoinMoin.mail.sendmail import decodeSpamSafeEmail

        if flaskg.user.valid:
            # decode address and generate mailto: link
            email = decodeSpamSafeEmail(email)
            result = moin_page.a(attrib={xlink.href: u'mailto:%s' % email}, children=[text or email])
        else:
            # unknown user, maybe even a spambot, so just return text as given in macro args
            if text:
                text += " "
            result = moin_page.code(children=[text, "<%s>" % email])

        return result

