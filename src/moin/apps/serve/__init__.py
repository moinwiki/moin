# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Serve external static files

For example, JavaScript-based drawing or HTML editors.
We avoid bundling them; instead, we access them somewhere on the
filesystem outside of Moin.
"""


from flask import Blueprint

serve = Blueprint("serve", __name__)
import moin.apps.serve.views  # noqa
