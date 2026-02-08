# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Feed views package

This package contains the views, templates, and static files for feeds (e.g., Atom).
"""

from flask import Blueprint

feed = Blueprint("feed", __name__)
import moin.apps.feed.views  # noqa
