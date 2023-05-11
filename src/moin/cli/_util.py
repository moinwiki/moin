# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin cli._util common functions used in cli
"""

from typing import Optional, Set

from flask import current_app as app
from moin.storage.backends.stores import Backend


def get_backends(backends: Optional[str], all_backends: bool) -> Set[Backend]:
    """return set of Backends for cli parameters
    :param backends: comma separated list of backends
    :param all_backends: True to include all backends, overrides backends parameter if True"""
    if all_backends:
        return set(app.cfg.backend_mapping.values())
    if backends:
        existing_backends = set(app.cfg.backend_mapping)
        backends = set(backends.split(','))
        if backends.issubset(existing_backends):
            return set([app.cfg.backend_mapping.get(backend_name) for backend_name in backends])
        else:
            print("Error: Wrong backend name given.")
            print("Given Backends: %r" % backends)
            print("Configured Backends: %r" % existing_backends)
    else:
        return set()
