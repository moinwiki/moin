# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MailTo Macro displays an E-Mail address (either a valid mailto: link for logged in users
or the obfuscated display passed as the first macro argument).
"""


from flask import g as flaskg

from moin.utils.tree import moin_page, xlink
from moin.macros._base import MacroInlineBase, fail_message
from moin.mail.sendmail import decodeSpamSafeEmail
from moin.i18n import _


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        """
        Invocation: <<MailTo(user AT example DOT org, write me)>>
        where 2nd parameter is optional.
        """
        if arguments:
            arguments = arguments[0].split(",")
        try:
            assert len(arguments) > 0 and len(arguments) < 3
            email = arguments[0]
            assert len(email) >= 5
        except (AttributeError, AssertionError):
            err_msg = _("Invalid format, try: <<MailTo(user AT example DOT org, write me)>>")
            return fail_message(err_msg, alternative)
        try:
            text = arguments[1]
        except IndexError:
            text = ""

        if flaskg.user.valid:
            # decode address and generate mailto: link
            email = decodeSpamSafeEmail(email)
            result = moin_page.a(attrib={xlink.href: f"mailto:{email}"}, children=[text or email])
        else:
            # unknown user, maybe even a spambot, so just return text as given in macro args
            if text:
                text += " "
            result = moin_page.code(children=[text, f"<{email}>"])

        return result
