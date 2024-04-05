# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - feed views package

    This package contains all views, templates, static files for feeds
    (like atom, ...).
"""


from flask import Blueprint

feed = Blueprint("feed", __name__)
import moin.apps.feed.views  # noqa
