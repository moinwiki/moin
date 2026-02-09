# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MailTo macro displays an email address.

For logged-in users, it shows a valid mailto: link; otherwise, it displays the
obfuscated string passed as the first macro argument.
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
        where the second parameter is optional.
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
            # Decode address and generate a mailto: link
            email = decodeSpamSafeEmail(email)
            result = moin_page.a(attrib={xlink.href: f"mailto:{email}"}, children=[text or email])
        else:
            # Unknown user (or spambot): return the text as given in the macro args.
            if text:
                text += " "
            result = moin_page.code(children=[text, f"<{email}>"])

        return result
