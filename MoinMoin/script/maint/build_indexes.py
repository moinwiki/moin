# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Build indexes
"""

import sys

from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option
from whoosh.filedb.multiproc import MultiSegmentWriter
from whoosh.index import create_in

from MoinMoin.search.indexing import WhooshIndex


class RebuildIndexes(Command):
    description = 'Build indexes'

    option_list = (
        Option('--procs', '-p', required=False, dest='procs', type=int, default=None,
            help='Number of processors the writer.'),
        Option('--limitmb', '-l', required=False, dest='limitmb', type=int, default=10,
            help='Maximum memory (in megabytes) each index-writer will use for the indexing pool.'),
        Option('--clean', action='store_true', dest='clean',
            help='Clear index files of given index-name. ATTENITON: use it only if your indexes broke, you had backup\
                  or just nothing to lose'),
        Option('--build', '-b', required=True, dest='build', type=str, choices=("all-revs", "latest-revs", "both"),
            help='What type of indexes we want to build. "all-revs", "latest-revs" or "both". Default: "both"'),
                  )

    # We use 3 separated functions because want to avoid checks and increase speed
    def run(self, procs, limitmb, build, clean):
        def build_both(clean):
            """Build indexes for all and latest revisions"""
            if clean:
                index_object.create_index(indexdir=app.cfg.index_dir,
                                         indexname="latest_revisions_index",
                                         schema="latest_revisions_schema"
                                        )
                index_object.create_index(indexdir=app.cfg.index_dir,
                                         indexname="all_revisions_index",
                                         schema="all_revisions_schema"
                                        )
            with MultiSegmentWriter(all_rev_index, procs, limitmb) as all_rev_writer:
                with MultiSegmentWriter(latest_rev_index, procs, limitmb) as latest_rev_writer:
                    for item in backend.iter_items_noindex():
                        for rev_no in item.list_revisions():
                            revision = item.get_revision(rev_no)
                            metadata = dict([(str(key), value)
                                             for key, value in revision.items()
                                             if key in all_rev_field_names])
                            metadata["rev_no"] = rev_no
                            all_rev_writer.add_document(**metadata)
                        # revision is now the latest revision of this item
                        metadata = dict([(str(key), value)
                                          for key, value in revision.items()
                                          if key in latest_rev_field_names])
                        metadata["rev_no"] = rev_no
                        latest_rev_writer.add_document(**metadata)

        def build_all_revs(clean):
            """Build indexes for all revisions"""
            if clean:
                index_object.create_index(indexdir=app.cfg.index_dir,
                                         indexname="all_revisions_index",
                                         schema="all_revisions_schema"
                                        )
            with MultiSegmentWriter(all_rev_index, procs, limitmb) as all_rev_writer:
                for item in backend.iter_items_noindex():
                    for rev_no in item.list_revisions():
                        revision = item.get_revision(rev_no)
                        metadata = dict([(str(key), value)
                                          for key, value in revision.items()
                                          if key in all_rev_field_names])
                        metadata["rev_no"] = rev_no
                        all_rev_writer.add_document(**metadata)

        def build_latest_revs(clean):
            """Build indexes for latest revisions"""
            if clean:
                index_object.create_index(indexdir=app.cfg.index_dir,
                                         indexname="latest_revisions_index",
                                         schema="latest_revisions_schema"
                                        )
            with MultiSegmentWriter(latest_rev_index, procs, limitmb) as latest_rev_writer:
                for item in backend.iter_items_noindex():
                    rev_no = max(item.list_revisions())
                    revision = item.get_revision(rev_no)
                    metadata = dict([(str(key), value)
                                      for key, value in revision.items()
                                      if key in latest_rev_field_names])
                    metadata["rev_no"] = rev_no
                    latest_rev_writer.add_document(**metadata)

        backend = flaskg.unprotected_storage = app.unprotected_storage
        index_object = WhooshIndex()
        latest_rev_index = index_object.latest_revisions_index
        latest_rev_field_names = latest_rev_index.schema.names()
        all_rev_index = index_object.all_revisions_index
        all_rev_field_names = all_rev_index.schema.names()

        if build == "both":
            build_both(clean)
        elif build == "all-revs":
            build_all_revs(clean)
        elif build == "latest-revs":
            build_latest_revs(clean)
