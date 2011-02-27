"""
    MoinMoin - serve (external) static files

    E.g. javascript based drawing or html editors.
    We want to avoid bundling them, thus we access them somewhere on the
    filesystem outside of moin.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from flask import Module
serve = Module(__name__)
import MoinMoin.apps.serve.views

