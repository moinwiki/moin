# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Admin views package

This package contains the views, templates, and static files for wiki administration.
"""

from flask import Blueprint

admin = Blueprint("admin", __name__, template_folder="templates")
import moin.apps.admin.views  # noqa
