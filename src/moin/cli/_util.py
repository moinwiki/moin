# Copyright: 2023 MoinMoin project
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - common utilities for CLI commands.
"""

from __future__ import annotations

from flask import current_app as app
from moin import log
from moin.storage.backends.stores import Backend

logging = log.getLogger(__name__)


def get_backends(backends: str | None, all_backends: bool) -> set[Backend]:
    """
    Return a set of Backends for CLI parameters.

    :param backends: Comma-separated list of backend names.
    :param all_backends: If True, include all backends (overrides 'backends').
    """
    if all_backends:
        return set(app.cfg.backend_mapping.values())

    if not backends:
        logging.warning("no backends specified")
        return set()

    existing_backends = set(app.cfg.backend_mapping)
    requested_backends = set(backends.split(","))
    if not requested_backends.issubset(existing_backends):
        print("Error: Wrong backend name given.")
        print("Given Backends: %r" % backends)
        print("Configured Backends: %r" % existing_backends)
        return set()

    return {app.cfg.backend_mapping.get(backend_name) for backend_name in requested_backends}


def drop_and_recreate_index(indexer, procs=None, limitmb=None, multisegment: bool = False) -> None:
    """
    Drop the index and recreate, rebuild, and optimize it.

    :param indexer: IndexingMiddleware object.
    :param procs: Number of processors the writer will use.
    :param limitmb: Maximum memory (in megabytes) each index writer will use for the indexing pool.
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
