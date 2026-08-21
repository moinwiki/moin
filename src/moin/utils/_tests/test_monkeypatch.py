# Copyright: 2026 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.monkeypatch tests.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from flask_theme import ThemeManager

from moin.utils import monkeypatch  # noqa: F401  ensures the patch below is applied


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
