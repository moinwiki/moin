# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Frontend views package

This package contains the views, templates, and static files that a typical wiki user sees.
"""


from flask import Blueprint

frontend = Blueprint("frontend", __name__)
import moin.apps.frontend.views  # noqa
