# Copyright: 2023 MoinMoin project
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin cli._util common functions used in cli
"""

from typing import Optional

from flask import current_app as app
from moin.storage.backends.stores import Backend
from moin import log

logging = log.getLogger(__name__)


def get_backends(backends: Optional[str], all_backends: bool) -> set[Backend]:
    """return set of Backends for cli parameters
    :param backends: comma separated list of backends
    :param all_backends: True to include all backends, overrides backends parameter if True"""
    if all_backends:
        return set(app.cfg.backend_mapping.values())
    if backends:
        existing_backends = set(app.cfg.backend_mapping)
        backends = set(backends.split(","))
        if backends.issubset(existing_backends):
            return {app.cfg.backend_mapping.get(backend_name) for backend_name in backends}
        else:
            print("Error: Wrong backend name given.")
            print("Given Backends: %r" % backends)
            print("Configured Backends: %r" % existing_backends)
    else:
        logging.warning("no backends specified")
        return set()


def drop_and_recreate_index(indexer, procs=None, limitmb=None, multisegment=False):
    """Drop index and recreate, rebuild and optimize
    :param indexer: IndexingMiddleware object
    :param procs: Number of processors the writer will use.
    :param limitmb: Maximum memory (in megabytes) each index-writer will use for the indexing pool
    """
    indexer.close()
    indexer.destroy()
    logging.debug("Create index")
    indexer.create()
    logging.debug("Rebuild index")
    # the use of multisegment leads to one index segment per process, the optimize step merges them later
    indexer.rebuild(procs=procs, limitmb=limitmb, multisegment=multisegment)
    logging.debug("Optimize index")
    indexer.optimize_index()
    indexer.open()
    logging.info("Rebuild index finished")
