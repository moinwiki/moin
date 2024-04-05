# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - misc. views package

    This package contains misc. stuff that doesn't fit into another view category.
"""


from flask import Blueprint

misc = Blueprint("misc", __name__, template_folder="templates")
import moin.apps.misc.views  # noqa
