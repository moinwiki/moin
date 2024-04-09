# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - admin views package

    This package contains all views, templates, static files for wiki administration.
"""


from flask import Blueprint

admin = Blueprint("admin", __name__, template_folder="templates")
import moin.apps.admin.views  # noqa
