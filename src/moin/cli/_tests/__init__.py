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


def read_index_dump_latest_revs(out: str):
    """parse output of moin dump-index yielding the items in latest revs

    :param out: stdout of `moin index-dump --no-truncate` command
    :return: list of dicts with key value pairs from output"""
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
