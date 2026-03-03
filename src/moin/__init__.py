# Copyright: 2000-2006 by Juergen Hermann <jh@web.de>
# Copyright: 2002-2018 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin — a wiki engine written in Python.
"""

from __future__ import annotations

import sys
import platform
import flask

from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:

    from .app import AppCtxGlobals, MoinApp

    current_app = cast(MoinApp, flask.current_app)
    g = cast(AppCtxGlobals, flask.g)

else:
    current_app = flask.current_app
    g = flask.g

flaskg = g  # deprecated, use g instead

from ._version import version  # noqa

project = "MoinMoin"

MIN_PYTHON_VERSION = (3, 10)

if sys.version_info < MIN_PYTHON_VERSION:
    sys.exit(
        f"Error: { project } requires Python { '.'.join(map(str, MIN_PYTHON_VERSION)) } or later; "
        f"current version is { platform.python_version() }"
    )
