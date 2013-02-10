# -*- coding: utf-8 -*-
# Copyright: 2003 Juergen Hermann <jh@web.de>
# Copyright: 2008-2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - email helper functions
"""


import os, re
from email.Header import Header

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app

from MoinMoin.constants.contenttypes import CHARSET
from MoinMoin.i18n import _, L_, N_

_transdict = {"AT": "@", "DOT": ".", "DASH": "-"}


def encodeAddress(address, charset):
    """
    Encode email address to enable non ascii names

    E.g. '"Jürgen Hermann" <jh@web.de>'. According to the RFC, the name
    part should be encoded, the address should not.

    :param address: email address, possibly using '"name" <address>' format
    :type address: unicode
    :param charset: specifying both the charset and the encoding, e.g
                    quoted printable or base64.
    :type charset: email.Charset.Charset instance
    :rtype: string
    :returns: encoded address
    """
    assert isinstance(address, unicode)
    composite = re.compile(r'(?P<phrase>.*?)(?P<blanks>\s*)\<(?P<addr>.*)\>', re.UNICODE)
    match = composite.match(address)
    if match:
        phrase = match.group('phrase')
        try:
            str(phrase)  # is it pure ascii?
        except UnicodeEncodeError:
            phrase = phrase.encode(CHARSET)
            phrase = Header(phrase, charset)
        blanks = match.group('blanks')
        addr = match.group('addr')
        if phrase:
            return "{0!s}{1!s}<{2!s}>".format(phrase, blanks, addr)
        else:
            return str(addr)
    else:
        # a pure email address, should encode to ascii without problem
        return str(address)


def sendmail(subject, text, to=None, cc=None, bcc=None, mail_from=None):
    """ Create and send a text/plain message

    Return a tuple of success or error indicator and message.

    :param subject: subject of email
    :type subject: unicode
    :param text: email body text
    :type text: unicode
    :param to: recipients
    :type to: list
    :param cc: recipients (CC)
    :type cc: list
    :param bcc: recipients (BCC)
    :type bcc: list
    :param mail_from: override default mail_from
    :type mail_from: unicode

    :rtype: tuple
    :returns: (is_ok, Description of error or OK message)
    """
    import smtplib, socket
    from email.Message import Message
    from email.Charset import Charset, QP
    from email.Utils import formatdate, make_msgid

    cfg = app.cfg
    if not cfg.mail_enabled:
        return (0, _("Contact administrator: cannot send password recovery e-mail because mail configuration is incomplete."))
    mail_from = mail_from or cfg.mail_from

    logging.debug("send mail, from: {0!r}, subj: {1!r}".format(mail_from, subject))
    logging.debug("send mail, to: {0!r}".format(to))

    if not to and not cc and not bcc:
        return (1, _("No recipients, nothing to do"))

    subject = subject.encode(CHARSET)

    # Create a text/plain body using CRLF (see RFC2822)
    text = text.replace(u'\n', u'\r\n')
    text = text.encode(CHARSET)

    # Create a message using CHARSET and quoted printable
    # encoding, which should be supported better by mail clients.
    # TODO: check if its really works better for major mail clients
    msg = Message()
    charset = Charset(CHARSET)
    charset.header_encoding = QP
    charset.body_encoding = QP
    msg.set_charset(charset)

    # work around a bug in python 2.4.3 and above:
    msg.set_payload('=')
    if msg.as_string().endswith('='):
        text = charset.body_encode(text)

    msg.set_payload(text)

    address = encodeAddress(mail_from, charset)
    msg['From'] = address
    if to:
        msg['To'] = ','.join(to)
    if cc:
        msg['CC'] = ','.join(cc)
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid()
    msg['Subject'] = Header(subject, charset)
    # See RFC 3834 section 5:
    msg['Auto-Submitted'] = 'auto-generated'

    if cfg.mail_sendmail:
        if bcc:
            # Set the BCC.  This will be stripped later by sendmail.
            msg['BCC'] = ','.join(bcc)
        # Set Return-Path so that it isn't set (generally incorrectly) for us.
        msg['Return-Path'] = address

    # Send the message
    if not cfg.mail_sendmail:
        try:
            logging.debug("trying to send mail (smtp) via smtp server '{0}'".format(cfg.mail_smarthost))
            host, port = (cfg.mail_smarthost + ':25').split(':')[:2]
            server = smtplib.SMTP(host, int(port))
            try:
                #server.set_debuglevel(1)
                if cfg.mail_username is not None and cfg.mail_password is not None:
                    try: # try to do tls
                        server.ehlo()
                        if server.has_extn('starttls'):
                            server.starttls()
                            server.ehlo()
                            logging.debug("tls connection to smtp server established")
                    except:
                        logging.debug("could not establish a tls connection to smtp server, continuing without tls")
                    logging.debug("trying to log in to smtp server using account '{0}'".format(cfg.mail_username))
                    server.login(cfg.mail_username, cfg.mail_password)
                server.sendmail(mail_from, (to or []) + (cc or []) + (bcc or []), msg.as_string())
            finally:
                try:
                    server.quit()
                except AttributeError:
                    # in case the connection failed, SMTP has no "sock" attribute
                    pass
        except smtplib.SMTPException as e:
            logging.exception("smtp mail failed with an exception.")
            return (0, str(e))
        except (os.error, socket.error) as e:
            logging.exception("smtp mail failed with an exception.")
            return (0, _("Connection to mailserver '%(server)s' failed: %(reason)s",
                server=cfg.mail_smarthost,
                reason=str(e)
            ))
    else:
        try:
            logging.debug("trying to send mail (sendmail)")
            sendmailp = os.popen(cfg.mail_sendmail, "w")
            # msg contains everything we need, so this is a simple write
            sendmailp.write(msg.as_string())
            sendmail_status = sendmailp.close()
            if sendmail_status:
                logging.error("sendmail failed with status: {0!s}".format(sendmail_status))
                return (0, str(sendmail_status))
        except:
            logging.exception("sendmail failed with an exception.")
            return (0, _("Mail not sent"))

    logging.debug("Mail sent successfully")
    return (1, _("Mail sent successfully"))


def encodeSpamSafeEmail(email_address, obfuscation_text=''):
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
        address = address.replace(sign, ' {0} '.format(word))
    if obfuscation_text.isalpha():
        # is the obfuscation_text alphabetic
        address = address.replace(' AT ', ' AT {0} '.format(obfuscation_text.upper()))

    return address

def decodeSpamSafeEmail(address):
    """ Decode obfuscated email address to standard email address

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
            word = _transdict.get(word, '')
        email.append(word)

    # return concatenated parts
    return ''.join(email)
