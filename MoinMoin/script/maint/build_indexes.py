# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Build indexes
"""


from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin.search.indexing import WhooshIndex


class RebuildIndexes(Command):
    description = 'Build indexes'

    def run(self):
        index_object = WhooshIndex()
        backend = flaskg.unprotected_storage = app.unprotected_storage
        latest_rev_index = index_object.latest_revisions_index
        latest_rev_field_names = latest_rev_index.schema.names()
        all_rev_index = index_object.all_revisions_index
        all_rev_field_names = all_rev_index.schema.names()
        with all_rev_index.writer() as all_rev_writer:
            for item in backend.iter_items_noindex():
                for rev_no in item.list_revisions():
                    revision = item.get_revision(rev_no)
                    metadata = {key: value
                                for key, value in revision.items()
                                if key in all_rev_field_names}
                    all_rev_writer.add_document(**metadata)
                # revision is now the latest revision of this item
                metadata = {key: value
                            for key, value in revision.items()
                            if key in latest_rev_field_names}
                with latest_rev_index.writer() as latest_rev_writer:
                    latest_rev_writer.add_document(**metadata)
