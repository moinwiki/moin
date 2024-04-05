# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - serve (external) static files

    E.g. javascript based drawing or html editors.
    We want to avoid bundling them, thus we access them somewhere on the
    filesystem outside of moin.
"""


from flask import Blueprint

serve = Blueprint("serve", __name__)
import moin.apps.serve.views  # noqa
