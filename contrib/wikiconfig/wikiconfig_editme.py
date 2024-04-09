"""
The intended use of wikiconfig_editme.py is for developers who want to add/remove
wikiconfig.py options for testing. Making quick changes in a small file can be
easier than editing a larger file.
"""

from wikiconfig import *
from moin.storage import create_simple_mapping


class LocalConfig(Config):
    pass
