# Copyright: 2003 Juergen Hermann <jh@web.de>
# Copyright: 2008-2009 MoinMoin:ThomasWaldmann
# Copyright: 2024-2025 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Email helper functions.
"""

import functools
import smtplib
import socket
import ssl

from email.message import EmailMessage
from email.utils import formatdate, getaddresses, make_msgid

from moin import current_app, log
from moin.i18n import _

logging = log.getLogger(__name__)

SMTP_TIMEOUT = 20.0
_transdict = {"AT": "@", "DOT": ".", "DASH": "-"}


@functools.cache
def _default_local_hostname():
    """Return the host name for the SMTP EHLO command and the Message-ID, like smtplib determines it.

    smtplib and make_msgid do this for every mail and need DNS lookups for it, which can take
    seconds if DNS does not work well. Do it only once per process.
    """
    fqdn = socket.getfqdn()
    if "." in fqdn:
        return fqdn
    # no FQDN found, use a domain literal (RFC 2821)
    addr = "127.0.0.1"
    try:
        addr = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        pass
    return f"[{addr}]"


def sendmail(subject, text, to=None, cc=None, bcc=None, mail_from=None, html=None):
    """Create and send a text/plain message.

    Return a tuple of success or error indicator and message.

    :param subject: subject of email
    :type subject: str
    :param text: email body text
    :type text: str
    :param to: recipients
    :type to: list of str
    :param cc: recipients (CC)
    :type cc: list of str
    :param bcc: recipients (BCC), not shown to any recipient
    :type bcc: list of str
    :param mail_from: override default mail_from
    :type mail_from: str
    :param html: HTML email body text
    :type html: str

    :rtype: tuple
    :returns: (is_ok, Description of error or OK message)
    """
    cfg = current_app.cfg
    if not cfg.mail_enabled:
        return (
            0,
            _(
                "Contact administrator: cannot send password recovery e-mail "
                "because mail configuration is incomplete."
            ),
        )
    mail_from = mail_from or cfg.mail_from
    if not mail_from:
        return 0, _("No sender address configured.")

    logging.debug(f"send mail, from: {mail_from!r}, subj: {subject!r}")
    logging.debug(f"send mail, to: {to!r}")

    if not to and not cc and not bcc:
        return 1, _("No recipients, nothing to do")

    local_hostname = cfg.mail_local_hostname or _default_local_hostname()

    msg = EmailMessage()

    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    msg["From"] = mail_from
    if to:
        msg["To"] = to
    if cc:
        msg["CC"] = cc
    if not to and not cc:
        # only BCC recipients, they must not see each other
        msg["To"] = "undisclosed-recipients:;"
    # the BCC recipients are only given to the SMTP server, never put into a header
    recipients = []
    for field in (to, cc, bcc):
        if field:
            # a field may also be a single string like "a@example.org, b@example.org"
            recipients += [addr for _, addr in getaddresses([field] if isinstance(field, str) else field) if addr]
    msg["Subject"] = subject
    msg["Date"] = formatdate()
    msg["Message-ID"] = make_msgid(domain=local_hostname)
    msg["Auto-Submitted"] = "auto-generated"  # RFC 3834 section 5

    # Connect to SMTP server
    try:
        host, port = (cfg.mail_smarthost + ":25").split(":")[:2]
        port = int(port)
        use_ssl = bool(port == 465)  # Use SMTP_SSL when the port is 465
        ssl_context = ssl.create_default_context()
    except (ValueError, ssl.SSLError) as e:
        logging.exception("SSL context creation failed: {reason}".format(reason=str(e)))
        return 0, _("SSL context creation failed: {reason}").format(reason=str(e))

    logging.debug(
        "Connecting to SMTP host=%s port=%s ssl=%s timeout=%s local_hostname=%s",
        host,
        port,
        use_ssl,
        SMTP_TIMEOUT,
        local_hostname,
    )

    try:
        server = None
        if use_ssl:
            server = smtplib.SMTP_SSL(
                host=host, port=port, local_hostname=local_hostname, timeout=SMTP_TIMEOUT, context=ssl_context
            )
            server.ehlo()
        else:
            server = smtplib.SMTP(host=host, port=port, local_hostname=local_hostname, timeout=SMTP_TIMEOUT)
            server.ehlo()
            try:  # try to use TLS
                if server.has_extn("starttls"):
                    server.starttls()
                    server.ehlo()
                    logging.debug("tls connection to smtp server established")
            except (smtplib.SMTPException, OSError) as e:
                logging.info("could not establish a tls connection to smtp server, continuing without tls")
                logging.info(f"reason: {e}")

        if cfg.mail_username and cfg.mail_password:
            logging.debug(f"trying to log in to smtp server using account '{cfg.mail_username}'")
            server.login(cfg.mail_username, cfg.mail_password)

        # Send the message
        server.send_message(msg, to_addrs=recipients)

    except (smtplib.SMTPException, OSError) as e:
        logging.exception(
            "Connection to mailserver '{server}' failed: {reason}".format(server=cfg.mail_smarthost, reason=str(e))
        )
        return 0, _("Connection to mailserver failed: {reason}").format(reason=str(e))

    finally:
        try:
            if server:
                server.quit()
        except AttributeError:
            # in case the connection failed, SMTP has no "sock" attribute
            pass

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
