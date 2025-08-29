# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Miscellaneous views package

This package contains miscellaneous views that do not fit into another category.
"""


from flask import Blueprint

misc = Blueprint("misc", __name__, template_folder="templates")
import moin.apps.misc.views  # noqa
