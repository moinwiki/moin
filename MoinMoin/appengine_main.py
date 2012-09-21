"""Main entry point for Google App Engine."""

import os
import sys

support_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'support'))
if support_path not in sys.path:
    sys.path.insert(0, support_path)

# Hack: If there are no DatastoreFile instances assume we must create the index.
from whoosh.filedb.gae import DatastoreFile
create_index = DatastoreFile.all().get() is None

# Create the WSGI application object.
from MoinMoin.app import create_app
application = create_app(create_index=create_index)
