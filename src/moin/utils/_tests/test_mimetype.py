# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.mimetype tests.
"""

from moin.utils.mimetype import MimeType


class TestMimeType:
    """
    Tests for moin.utils.mimetype.
    """

    def test_parse_format(self):
        mimettype = MimeType.from_filename("test_file.jpg")
        # format in PARSER_TEXT_MIMETYPE
        test = [
            # test_format, test_mimetype
            ("html", ("text", "html")),
            ("css", ("text", "css")),
            ("python", ("text", "python")),
            ("latex", ("text", "latex")),
        ]

        for test_format, test_mimetype in test:
            result = mimettype.parse_format(test_format)
            assert result == test_mimetype

        # format not in PARSER_TEXT_MIMETYPE
        test = [
            # test_format, test_mimetype
            ("wiki", ("text", "x.moin.wiki")),
            ("irc", ("text", "irssi")),
            ("test_random", ("text", "x-test_random")),
        ]

        for test_format, test_mimetype in test:
            result = mimettype.parse_format(test_format)
            assert result == test_mimetype

    def test_mime_type(self):
        test = [
            # test_extension, test_major/minor
            (".mpeg", "video/mpeg"),
            (".pdf", "application/pdf"),
            (".txt", "text/plain"),
            (".jpeg", "image/jpeg"),
            (".png", "image/png"),
            (".svg", "image/svg+xml"),
            (".tar.bz2", "application/x-tar"),
            (".tar.gz", "application/x-tar"),
            (".tar.xz", "application/x-tar"),
            (".tar.zip", "application/zip"),
            (".xml.bz2", "application/x-bzip2"),
            (".xml.gz", "application/gzip"),
            (".xml.xz", "application/x-xz"),
            (".xml.zip", "application/zip"),
            ("", "application/octet-stream"),
        ]

        # when mimestr is None
        for test_extension, test_major_minor in test:
            mimetype = MimeType.from_filename("test_file" + test_extension)
            result = mimetype.mime_type()
            expected = test_major_minor
            assert result == expected

        # when mimestr is not None
        mimetype = MimeType('image/jpeg;charset="utf-8";misc=moin_misc')
        result = mimetype.mime_type()
        assert result == "image/jpeg"

    def test_content_type(self):
        mimetype = MimeType("test_file.mpeg")

        result1 = mimetype.content_type(major="application", minor="pdf", charset="utf-16", params=None)
        expected = "application/pdf"
        assert result1 == expected

        # major == 'text'
        result2 = mimetype.content_type(major="text", minor="plain", charset="utf-16", params=None)
        expected = 'text/plain;charset="utf-16"'
        assert result2 == expected

        # when all the parameters passed are None
        result3 = mimetype.content_type()
        expected = "text/x-test_file.mpeg"
        assert result3 == expected
