# Copyright: 2003 Juergen Hermann <jh@web.de>
# Copyright: 2008-2009 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - email helper functions
"""


import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from flask import current_app as app

from moin.i18n import _

from moin import log

logging = log.getLogger(__name__)


_transdict = {"AT": "@", "DOT": ".", "DASH": "-"}


def sendmail(subject, text, to=None, cc=None, bcc=None, mail_from=None, html=None):
    """Create and send a text/plain message

    Return a tuple of success or error indicator and message.

    :param subject: subject of email
    :type subject: str
    :param text: email body text
    :type text: str
    :param to: recipients
    :type to: list of str
    :param cc: recipients (CC)
    :type cc: list of str
    :param bcc: recipients (BCC)
    :type bcc: list of str
    :param mail_from: override default mail_from
    :type mail_from: str
    :param html: html email body text
    :type html: str

    :rtype: tuple
    :returns: (is_ok, Description of error or OK message)
    """
    cfg = app.cfg
    if not cfg.mail_enabled:
        return (
            0,
            _(
                "Contact administrator: cannot send password recovery e-mail "
                "because mail configuration is incomplete."
            ),
        )
    mail_from = mail_from or cfg.mail_from

    logging.debug(f"send mail, from: {mail_from!r}, subj: {subject!r}")
    logging.debug(f"send mail, to: {to!r}")

    if not to and not cc and not bcc:
        return 1, _("No recipients, nothing to do")

    msg = EmailMessage()

    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    msg["From"] = mail_from
    if to:
        msg["To"] = to
    if cc:
        msg["CC"] = cc
    msg["Subject"] = subject
    msg["Date"] = formatdate()
    msg["Message-ID"] = make_msgid()
    msg["Auto-Submitted"] = "auto-generated"  # RFC 3834 section 5

    if cfg.mail_sendmail:
        if bcc:
            # Set the BCC.  This will be stripped later by sendmail.
            msg["BCC"] = bcc
        # Set Return-Path so that it isn't set (generally incorrectly) for us.
        msg["Return-Path"] = mail_from

    # Send the message
    if not cfg.mail_sendmail:
        try:
            logging.debug(f"trying to send mail (smtp) via smtp server '{cfg.mail_smarthost}'")
            host, port = (cfg.mail_smarthost + ":25").split(":")[:2]
            server = smtplib.SMTP(host, int(port))
            try:
                server.ehlo()
                try:  # try to do TLS
                    if server.has_extn("starttls"):
                        server.starttls()
                        server.ehlo()
                        logging.debug("tls connection to smtp server established")
                except Exception:
                    logging.debug("could not establish a tls connection to smtp server, continuing without tls")
                # server.set_debuglevel(1)
                if cfg.mail_username is not None and cfg.mail_password is not None:
                    logging.debug(f"trying to log in to smtp server using account '{cfg.mail_username}'")
                    server.login(cfg.mail_username, cfg.mail_password)
                server.send_message(msg)
            finally:
                try:
                    server.quit()
                except AttributeError:
                    # in case the connection failed, SMTP has no "sock" attribute
                    pass
        except smtplib.SMTPException as e:
            logging.exception("smtp mail failed with an exception.")
            return 0, str(e)
        except OSError as e:
            logging.exception("smtp mail failed with an exception.")
            return (
                0,
                _("Connection to mailserver '{server}' failed: {reason}").format(
                    server=cfg.mail_smarthost, reason=str(e)
                ),
            )
    else:
        raise NotImplementedError  # TODO cli sendmail support

    logging.debug("Mail sent successfully")
    return 1, _("Mail sent successfully")


def encodeSpamSafeEmail(email_address, obfuscation_text=""):
    """
    Encodes a standard email address to an obfuscated address

    :param email_address: mail address to encode.
                          Known characters and their all-uppercase words translation::

                              "." -> " DOT "
                              "@" -> " AT "
                              "-" -> " DASH "
    :param obfuscation_text: optional text to obfuscate the email.
                             All characters in the string must be alphabetic
                             and they will be added in uppercase.
    """
    address = email_address.lower()
    # uppercase letters will be stripped by decodeSpamSafeEmail
    for word, sign in _transdict.items():
        address = address.replace(sign, f" {word} ")
    if obfuscation_text.isalpha():
        # is the obfuscation_text alphabetic
        address = address.replace(" AT ", f" AT {obfuscation_text.upper()} ")

    return address


def decodeSpamSafeEmail(address):
    """Decode obfuscated email address to standard email address

    Decode a spam-safe email address in `address` by applying the
    following rules:

    Known all-uppercase words and their translation:
        "DOT"   -> "."
        "AT"    -> "@"
        "DASH"  -> "-"

    Any unknown all-uppercase words or an uppercase letter simply get stripped.
    Use that to make it even harder for spam bots!

    Blanks (spaces) simply get stripped.

    :param address: obfuscated email address string
    :rtype: string
    :returns: decoded email address
    """
    email = []

    # words are separated by blanks
    for word in address.split():
        # is it all-uppercase?
        if word.isalpha() and word == word.upper():
            # strip unknown CAPS words
            word = _transdict.get(word, "")
        email.append(word)

    # return concatenated parts
    return "".join(email)
