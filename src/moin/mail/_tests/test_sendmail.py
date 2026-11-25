# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.mail.sendmail tests.
"""

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
    """Stands in for smtplib.SMTP, records the local_hostname of each connection."""

    local_hostnames = []

    def __init__(self, host, port, local_hostname=None, timeout=None):
        self.local_hostnames.append(local_hostname)

    def ehlo(self):
        pass

    def has_extn(self, name):
        return False

    def send_message(self, msg):
        pass

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
    # do not keep host names faked by a test cached for other tests
    sendmail._default_local_hostname.cache_clear()
    request.addfinalizer(sendmail._default_local_hostname.cache_clear)
    return cfg


def send():
    is_ok, msg = sendmail.sendmail("subject", "text", to=["user@example.org"])
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
    messages = []
    monkeypatch.setattr(mail_cfg, "mail_local_hostname", "wiki.example.org")
    monkeypatch.setattr(sendmail.socket, "getfqdn", lambda: "other.example.org")
    monkeypatch.setattr(FakeSMTP, "send_message", lambda self, msg: messages.append(msg))
    send()
    assert messages[0]["Message-ID"].endswith("@wiki.example.org>")
