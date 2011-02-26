"""
    MoinMoin - frontend views package

    This package contains all views, templates, static files that a normal wiki
    user usually sees.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from flask import Module
frontend = Module(__name__)
import MoinMoin.apps.frontend.views

