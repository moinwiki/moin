"""
    MoinMoin - feed views package

    This package contains all views, templates, static files for feeds
    (like atom, ...).

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from flask import Module
feed = Module(__name__)
import MoinMoin.apps.feed.views

