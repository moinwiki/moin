# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.mail.sendmail tests.
"""

import re
import smtplib

import pytest

from moin import current_app
from moin.mail import sendmail


class TestdecodeSpamSafeEmail:
    """mail.sendmail: testing decodeSpamSafeEmail."""

    _tests = (
        ("", ""),
        ("AT", "@"),
        ("DOT", "."),
        ("DASH", "-"),
        ("CAPS", ""),
        ("Mixed", "Mixed"),
        ("lower", "lower"),
        ("Firstname DOT Lastname AT example DOT net", "Firstname.Lastname@example.net"),
        ("Firstname . Lastname AT exa mp le DOT n e t", "Firstname.Lastname@example.net"),
        ("Firstname I DONT WANT SPAM . Lastname@example DOT net", "Firstname.Lastname@example.net"),
        ("First name I Lastname DONT AT WANT SPAM example DOT n e t", "FirstnameLastname@example.net"),
        ("first.last@example.com", "first.last@example.com"),
        ("first . last @ example . com", "first.last@example.com"),
    )

    def testDecodeSpamSafeMail(self):
        """mail.sendmail: decoding spam-safe email addresses."""
        for coded, expected in self._tests:
            assert sendmail.decodeSpamSafeEmail(coded) == expected


class TestencodeSpamSafeEmail:
    """mail.sendmail: testing encodeSpamSafeEmail (spam-safe encoding)."""

    _tests = (
        ("", ""),
        ("@", " AT "),
        (".", " DOT "),
        ("-", " DASH "),
        ("lower", "lower"),
        ("Firstname.Lastname@example.net", "firstname DOT lastname AT example DOT net"),
        ("F.Lastname@example.net", "f DOT lastname AT example DOT net"),
    )

    def testEncodeSpamSafeMail(self):
        """mail.sendmail: encoding email addresses to spam-safe format."""
        for coded, expected in self._tests:
            assert sendmail.encodeSpamSafeEmail(coded) == expected

    def testEncodeSpamSafeMailAndObfuscate(self):
        """mail.sendmail: encoding email addresses with an obfuscation string to spam-safe format."""
        for coded, expected in self._tests:
            expected = expected.replace(" AT ", " AT SYCTE ")
            assert sendmail.encodeSpamSafeEmail(coded, "SYCTE") == expected


coverage_modules = ["moin.mail.sendmail"]


class FakeSMTP:
    """Stands in for smtplib.SMTP, records the local_hostname of each connection and what is sent."""

    local_hostnames = []
    sent = []  # (envelope recipients, message as sent)

    def __init__(self, host, port, local_hostname=None, timeout=None):
        self.local_hostnames.append(local_hostname)

    def ehlo(self):
        pass

    ehlo_or_helo_if_needed = ehlo

    def has_extn(self, name):
        return False

    # the real one, it decides which recipients and headers get sent
    send_message = smtplib.SMTP.send_message

    def sendmail(self, from_addr, to_addrs, msg, mail_options=(), rcpt_options=()):
        self.sent.append((to_addrs, msg.decode()))

    def quit(self):
        pass


@pytest.fixture
def mail_cfg(_app_ctx, monkeypatch, request):
    cfg = current_app.cfg
    monkeypatch.setattr(cfg, "mail_smarthost", "smtp.example.org")
    monkeypatch.setattr(cfg, "mail_from", "wiki@example.org")
    monkeypatch.setattr(cfg, "mail_enabled", True)
    monkeypatch.setattr(sendmail.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(FakeSMTP, "local_hostnames", [])
    monkeypatch.setattr(FakeSMTP, "sent", [])
    # do not keep host names faked by a test cached for other tests
    sendmail._default_local_hostname.cache_clear()
    request.addfinalizer(sendmail._default_local_hostname.cache_clear)
    return cfg


def send(**recipients):
    is_ok, msg = sendmail.sendmail("subject", "text", **(recipients or dict(to=["user@example.org"])))
    assert is_ok, msg


def test_configured_local_hostname(mail_cfg, monkeypatch):
    def getfqdn():
        raise AssertionError("no DNS lookup expected")

    monkeypatch.setattr(mail_cfg, "mail_local_hostname", "wiki.example.org")
    monkeypatch.setattr(sendmail.socket, "getfqdn", getfqdn)
    send()
    assert FakeSMTP.local_hostnames == ["wiki.example.org"]


def test_local_hostname_looked_up_once(mail_cfg, monkeypatch):
    lookups = []

    def getfqdn():
        lookups.append(1)
        return "host.example.org"

    monkeypatch.setattr(sendmail.socket, "getfqdn", getfqdn)
    send()
    send()
    assert FakeSMTP.local_hostnames == ["host.example.org", "host.example.org"]
    assert len(lookups) == 1


def test_local_hostname_without_fqdn(mail_cfg, monkeypatch):
    monkeypatch.setattr(sendmail.socket, "getfqdn", lambda: "host")
    monkeypatch.setattr(sendmail.socket, "gethostbyname", lambda name: "192.0.2.1")
    send()
    assert FakeSMTP.local_hostnames == ["[192.0.2.1]"]


def test_message_id_uses_local_hostname(mail_cfg, monkeypatch):
    monkeypatch.setattr(mail_cfg, "mail_local_hostname", "wiki.example.org")
    monkeypatch.setattr(sendmail.socket, "getfqdn", lambda: "other.example.org")
    send()
    [(envelope, msg)] = FakeSMTP.sent
    assert re.search(r"^Message-ID: <[^>]+@wiki\.example\.org>\r?$", msg, re.MULTILINE)


def test_bcc(mail_cfg):
    send(to=["user@example.org"], bcc=["hidden@example.org", "Other <other@example.org>"])
    [(envelope, msg)] = FakeSMTP.sent
    assert envelope == ["user@example.org", "hidden@example.org", "other@example.org"]
    assert "To: user@example.org" in msg
    assert "hidden@example.org" not in msg
    assert "other@example.org" not in msg
    assert "Bcc" not in msg


def test_only_bcc(mail_cfg):
    send(bcc=["one@example.org", "two@example.org"])
    [(envelope, msg)] = FakeSMTP.sent
    assert envelope == ["one@example.org", "two@example.org"]
    assert "To: undisclosed-recipients:;" in msg
    assert "one@example.org" not in msg
    assert "two@example.org" not in msg


def test_to_as_string(mail_cfg):
    send(to="one@example.org, Two <two@example.org>")
    [(envelope, msg)] = FakeSMTP.sent
    assert envelope == ["one@example.org", "two@example.org"]
