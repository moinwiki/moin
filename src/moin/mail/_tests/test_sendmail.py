# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.mail.sendmail Tests
"""


from moin.mail import sendmail


class TestdecodeSpamSafeEmail:
    """mail.sendmail: testing mail"""

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
        """mail.sendmail: decoding spam safe mail"""
        for coded, expected in self._tests:
            assert sendmail.decodeSpamSafeEmail(coded) == expected


class TestencodeSpamSafeEmail:
    """mail.sendmail: testing spam safe mail"""

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
        """mail.sendmail: encoding mail address to spam safe mail"""
        for coded, expected in self._tests:
            assert sendmail.encodeSpamSafeEmail(coded) == expected

    def testEncodeSpamSafeMailAndObfuscate(self):
        """mail.sendmail: encoding mail address by an obfuscate string to spam safe mail"""
        for coded, expected in self._tests:
            expected = expected.replace(" AT ", " AT SYCTE ")
            assert sendmail.encodeSpamSafeEmail(coded, "SYCTE") == expected


coverage_modules = ["moin.mail.sendmail"]
