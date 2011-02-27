"""
    MoinMoin - admin views package

    This package contains all views, templates, static files for wiki administration.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from flask import Module
admin = Module(__name__)
import MoinMoin.apps.admin.views

