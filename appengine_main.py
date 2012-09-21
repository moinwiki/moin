"""Main entry point for Google App Engine."""

# Python imports.
import os
import sys

# Tweak sys.path.
support_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'support'))
if support_path not in sys.path:
    sys.path.insert(0, support_path)

# Now we can import MoinMoin.
from MoinMoin.app import create_app

# Hack: If there are no DatastoreFile instances assume we must create the index.
from whoosh.filedb.gae import DatastoreFile
create_index = DatastoreFile.all().get() is None

# Create the WSGI application object.
application = create_app(create_index=create_index)
