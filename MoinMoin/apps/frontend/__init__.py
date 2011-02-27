"""
    MoinMoin - frontend views package

    This package contains all views, templates, static files that a normal wiki
    user usually sees.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from flask import Module
frontend = Module(__name__)
import MoinMoin.apps.frontend.views

