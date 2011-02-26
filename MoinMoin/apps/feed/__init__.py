"""
    MoinMoin - feed views package

    This package contains all views, templates, static files for feeds
    (like atom, ...).

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from flask import Module
feed = Module(__name__)
import MoinMoin.apps.feed.views

