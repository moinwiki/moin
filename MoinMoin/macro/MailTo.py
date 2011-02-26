"""
    MoinMoin - MailTo Macro displays an E-Mail address (either a valid mailto:
    link for logged in users or an obfuscated display as given as the macro argument.

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from flask import flaskg

from MoinMoin.util.tree import moin_page, xlink
from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, email=unicode, text=u''):
        if not email:
            raise ValueError("You need to give an (obfuscated) email address")

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





