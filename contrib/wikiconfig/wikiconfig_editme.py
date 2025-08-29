"""
The intended use of wikiconfig_editme.py is to let developers add or remove
wikiconfig.py options for testing. Making quick changes in this small file can be
easier than editing a larger file.
"""

from wikiconfig import *
from moin.storage import create_simple_mapping


class LocalConfig(Config):
    pass
