# Copyright: 2026 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.monkeypatch tests.
"""

from __future__ import annotations

import threading
import time
from io import BytesIO
from types import SimpleNamespace

import pytest

from flask_theme import ThemeManager
from whoosh.fields import ID, TEXT, Schema
from whoosh.filedb import structfile
from whoosh.filedb.filestore import FileStorage
from whoosh.filedb.structfile import BufferFile, StructFile
from whoosh.query import Term

# importing moin.utils.monkeypatch applies the patches tested below
from moin.utils.monkeypatch import BufferReader


def _slow_loader(app):
    """
    A fake theme loader that stalls before producing anything, widening
    the refresh() race window enough to reliably hit it in a test (the
    real window, scanning the filesystem for theme directories, is
    normally far too narrow to hit deterministically). time.sleep()
    releases the GIL, so this also guarantees other threads actually get
    to run during the window instead of merely making it wider in theory.
    """
    time.sleep(0.05)
    yield SimpleNamespace(application="test-app", identifier="topside")
    yield SimpleNamespace(application="test-app", identifier="modernized")


def _make_manager():
    return ThemeManager(SimpleNamespace(), "test-app", loaders=[_slow_loader])


def test_theme_manager_first_population_is_race_free():
    """
    Regression test: on a freshly-started/recycled mod_wsgi process,
    ThemeManager._themes is None and several threads can take their first
    request around the same moment. Each thread's first `.themes` access
    sees `_themes is None` and calls refresh() -- but the original
    flask_theme implementation reset self._themes to an empty dict before
    slowly repopulating it, so a second thread's `_themes is None` check
    (already False, since the first thread already set it to {}) returned
    the still-empty dict directly, without doing its own refresh --
    raising a spurious KeyError for a theme (e.g. the configured default)
    that's about to exist a moment later.
    """
    manager = _make_manager()
    assert manager._themes is None  # nothing populated yet, like a fresh process

    errors = []

    def reader():
        try:
            manager.themes["topside"]
        except KeyError as e:
            errors.append(e)

    threads = [threading.Thread(target=reader) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"{len(errors)} of {len(threads)} concurrent first-time readers saw a spurious KeyError"


def test_theme_manager_concurrent_refresh_is_race_free():
    """
    Regression test: moin's get_current_theme() retries a KeyError by
    forcing current_app.theme_manager.refresh() and looking up the theme
    again. If another thread is concurrently doing the same thing (or just
    reading .themes) against an already-populated registry, the original
    refresh() briefly made even a *previously present* theme disappear,
    so that retry could itself fail with the same KeyError.
    """
    manager = _make_manager()
    manager.refresh()
    assert "topside" in manager.themes  # a warm, complete registry, like steady state

    errors = []
    stop = threading.Event()

    def reader():
        # loop for as long as the refresher is running, not a fixed count --
        # a fixed count of fast dict lookups can finish before the refresher
        # thread is even scheduled, missing the window entirely
        while not stop.is_set():
            try:
                manager.themes["topside"]
            except KeyError as e:
                errors.append(e)

    def refresh_then_stop():
        manager.refresh()
        stop.set()

    readers = [threading.Thread(target=reader) for _ in range(8)]
    refresher = threading.Thread(target=refresh_then_stop)

    for t in readers:
        t.start()
    refresher.start()
    refresher.join()
    for t in readers:
        t.join()

    assert not errors, f"{len(errors)} reads saw a spurious KeyError during a concurrent refresh"


# whoosh BufferFile: read without copying the buffer

DATA = b"first line\nsecond line\n\nlast line without newline"


def apply(f, op):
    name, *args = op
    return getattr(f, name)(*args)


@pytest.mark.parametrize(
    "ops",
    [
        [("read", 5), ("read", 3), ("tell",), ("read",)],
        [("read", 0), ("read", -1), ("read", 1), ("read", None)],
        [("seek", 3), ("read", 4), ("seek", 2, 1), ("read", 2), ("seek", -4, 2), ("read", 10), ("tell",)],
        [("seek", 1000), ("read", 3), ("tell",), ("readline",)],
        [("readline",), ("readline",), ("readline",), ("readline",), ("readline",)],
        [("readline", 4), ("readline", 100), ("readline", 0), ("tell",)],
    ],
)
def test_reader_like_bytesio(ops):
    for buf in (DATA, memoryview(DATA)):
        reader, bytesio = BufferReader(buf), BytesIO(DATA)
        assert [apply(reader, op) for op in ops] == [apply(bytesio, op) for op in ops]


def test_reader_long_line_and_iteration():
    data = b"x" * 10000 + b"\n" + b"y" * 5000
    assert list(BufferReader(memoryview(data))) == list(BytesIO(data))


def test_reader_errors():
    reader = BufferReader(DATA)
    with pytest.raises(ValueError):
        reader.seek(-1)
    with pytest.raises(ValueError):
        reader.seek(0, 3)
    reader.close()
    assert reader.closed
    with pytest.raises(ValueError):
        reader.read()


def test_buffer_file_reads_without_copy(monkeypatch):
    out = StructFile(BytesIO())
    out.write_varint(300)
    out.write_int(-7)
    out.write_string(b"moin")
    out.write_long(2**40)
    data = out.file.getvalue()

    def no_copy(*args):
        raise AssertionError("BufferFile must not copy its buffer into a BytesIO")

    monkeypatch.setattr(structfile, "BytesIO", no_copy)
    f = BufferFile(memoryview(data))
    assert (f.read_varint(), f.read_int(), f.read_string(), f.read_long()) == (300, -7, b"moin", 2**40)
    f.seek(0)
    assert f.read_varint() == 300
    sub = f.subset(0, 2)
    assert sub.read_varint() == 300
    f.close()


def test_index_on_disk(tmp_path, monkeypatch):
    # whoosh memory-maps the segment files of a FileStorage index and reads them via BufferFile
    schema = Schema(name=ID(stored=True, unique=True), content=TEXT(stored=True))
    ix = FileStorage(str(tmp_path)).create_index(schema)
    for i in range(3):  # one segment per commit
        with ix.writer() as writer:
            writer.add_document(name=f"item{i}", content=f"some text number{i}")

    def no_copy(*args):
        raise AssertionError("BufferFile must not copy its buffer into a BytesIO")

    monkeypatch.setattr(structfile, "BytesIO", no_copy)
    with ix.searcher() as searcher:
        assert searcher.doc_count() == 3
        assert [hit["name"] for hit in searcher.search(Term("content", "number1"))] == ["item1"]
        assert searcher.document(name="item2")["content"] == "some text number2"
        assert sorted(searcher.lexicon("name")) == [b"item0", b"item1", b"item2"]
