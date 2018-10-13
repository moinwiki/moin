# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MailTo Macro displays an E-Mail address (either a valid mailto: link for logged in users
or the obfuscated display passed as the first macro argument).
"""


from flask import g as flaskg

from moin.util.tree import moin_page, xlink
from moin.macros._base import MacroInlineBase
from moin.mail.sendmail import decodeSpamSafeEmail
from moin.converter._args_wiki import parse as parse_arguments
from moin.i18n import _, L_, N_


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        """
        Invocation: <<MailTo(user AT example DOT org, write me)>>
        where 2nd parameter is optional.
        """
        if arguments:
            arguments = arguments[0].split(',')
        try:
            assert len(arguments) > 0 and len(arguments) < 3
            email = arguments[0]
            assert len(email) >= 5
        except (AttributeError, AssertionError):
            raise ValueError(_("MailTo: invalid format, try: <<MailTo(user AT example DOT org, write me)>>"))

        try:
            text = arguments[1]
        except IndexError:
            text = u''

        if flaskg.user.valid:
            # decode address and generate mailto: link
            email = decodeSpamSafeEmail(email)
            result = moin_page.a(attrib={xlink.href: u'mailto:{0}'.format(email)}, children=[text or email])
        else:
            # unknown user, maybe even a spambot, so just return text as given in macro args
            if text:
                text += " "
            result = moin_page.code(children=[text, "<{0}>".format(email)])

        return result
