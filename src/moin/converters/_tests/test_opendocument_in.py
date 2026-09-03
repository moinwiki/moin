# Copyright: 2026 MoinMoin:RikvanRiel
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for the OpenDocument indexing converter.
"""

import io
import struct
import zipfile
from types import SimpleNamespace
from typing import Any

from moin.constants.keys import NAME
from moin.converters import default_registry
from moin.converters.opendocument_in import OpenDocumentIndexingConverter
from moin.utils.mime import Type, type_text_plain


def make_rev(data: bytes) -> Any:
    return SimpleNamespace(data=io.BytesIO(data), meta={NAME: "test.odt"})


def convert(data: bytes) -> str:
    return OpenDocumentIndexingConverter()(make_rev(data))


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_garbage_returns_empty():
    """Garbage bytes raise BadZipFile in ZipFile construction, outside the old try."""
    assert convert(b"this is not a zip file") == ""


def test_zip_missing_content_xml_returns_empty():
    """A valid zip without content.xml raises KeyError, which the old code let escape."""
    assert convert(make_zip({"mimetype": b"application/vnd.oasis.opendocument.text"})) == ""


def test_content_xml_bad_utf8_returns_empty():
    """A content.xml that is not valid UTF-8 raises UnicodeDecodeError on decode."""
    assert convert(make_zip({"content.xml": b"\xff\xfe\x00not utf-8"})) == ""


def test_valid_odt_returns_text():
    """A well-formed ODT still indexes its text content."""
    assert convert(make_zip({"content.xml": b"<doc><p>Hello ODT</p></doc>"})) == "Hello ODT"


def test_registry_two_arg_call_returns_text():
    """convert_to_indexable() calls converter(revision, input_contenttype).

    The old (self, rev) signature raised TypeError on that call shape for
    every ODT, valid ones included; the one-arg tests above bypass it.
    """
    converter = default_registry.get(Type("application/vnd.oasis.opendocument.text"), type_text_plain)
    data = make_zip({"content.xml": b"<doc><p>Hello ODT</p></doc>"})
    assert converter(make_rev(data), "application/vnd.oasis.opendocument.text") == "Hello ODT"


def make_deflated_odt() -> bytearray:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.xml", b"<doc><p>Hello ODT</p></doc>")
    return bytearray(buf.getvalue())


def convert_registry(data: bytes) -> str:
    converter = default_registry.get(Type("application/vnd.oasis.opendocument.text"), type_text_plain)
    return converter(make_rev(data), "application/vnd.oasis.opendocument.text")


def test_corrupt_deflate_returns_empty():
    """A corrupt deflate stream raises zlib.error, which the old code let escape."""
    data = make_deflated_odt()
    local = data.find(b"PK\x03\x04")
    extra_len = struct.unpack_from("<H", data, local + 28)[0]
    data_off = local + 30 + len(b"content.xml") + extra_len
    for i in range(10):
        data[data_off + i] ^= 0xFF
    assert convert_registry(bytes(data)) == ""


def test_encrypted_member_returns_empty():
    """An encrypted member raises RuntimeError, which the old code let escape."""
    data = make_deflated_odt()
    local = data.find(b"PK\x03\x04")
    central = data.find(b"PK\x01\x02")
    assert data.find(b"content.xml", central, central + 60) != -1
    data[local + 6] |= 0x01
    data[central + 8] |= 0x01
    assert convert_registry(bytes(data)) == ""


def test_unsupported_method_returns_empty():
    """An unknown compression method raises NotImplementedError, which the old code let escape."""
    data = make_deflated_odt()
    local = data.find(b"PK\x03\x04")
    central = data.find(b"PK\x01\x02")
    assert data.find(b"content.xml", central, central + 60) != -1
    struct.pack_into("<H", data, local + 8, 99)
    struct.pack_into("<H", data, central + 10, 99)
    assert convert_registry(bytes(data)) == ""
