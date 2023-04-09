# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli common functions for tests
"""

from copy import copy
import datetime  # noqa
import os
import subprocess
from typing import List

from moin import log

logging = log.getLogger(__name__)


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    """run a shell command, capturing output"""
    subprocess_environ = copy(os.environ)
    subprocess_environ['PYTHONIOENCODING'] = 'cp1252'  # simulate windows terminal to ferret out encoding issues
    logging.info(f'running {cmd}')
    return subprocess.run(cmd, capture_output=True, env=subprocess_environ)


def assert_p_succcess(p: subprocess.CompletedProcess):
    """assert returncode 0 and print logs on error"""
    try:
        assert p.returncode == 0
    except AssertionError:
        logging.error(f'failure for {p.args} stdout = {p.stdout} stderr = {p.stderr}')
        raise


def read_index_dump_latest_revs(out: str):
    """parse output of moin dump-index yielding the items in latest revs

    :param out: stdout of `moin index-dump --no-truncate` command
    :return: list of dicts with key value pairs from output"""
    if not isinstance(out, str):
        raise ValueError('read_index_dump_latest_revs expects str, did you forget to .decode()')
    item = {}
    for line in out.splitlines():
        if not line.strip() or line.startswith(' '):
            if item:
                yield item
                item = {}
            if 'all_revs' in line:
                break
            continue
        space_index = line.index(' ')
        item[line[0:space_index]] = eval(line[space_index + 1:])
