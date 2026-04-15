# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Flask application modules

This package contains the following Flask blueprints:

- frontend: the user-facing wiki interface
- feed: feed-related functionality
- admin: administrative views for wiki administrators
- serve: static file serving
"""

from .admin import admin
from .feed import feed
from .frontend import frontend
from .misc import misc
from .serve import serve

__all__ = ["admin", "feed", "frontend", "misc", "serve"]
