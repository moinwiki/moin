# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli common functions for tests
"""

from copy import copy
import datetime  # noqa
import os
import re
import subprocess
from typing import List
from warnings import warn

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


ARRAY_SPLIT_RE = re.compile(r'[\[\],]')
DATETIME_RE = re.compile(r'datetime\.datetime\([\d, ]*\)')
COUNT_SLASHES_RE = re.compile(r'([\\]*)$')


def _is_eval_safe(s: str) -> bool:
    """validate that s is one of the expected formats in output of moin index-dump

    valid strings include
    'a string'
    'a string doesn\'t have to be simple'
    ['one', 'two']
    []
    123
    datetime.datetime(2023, 4, 17, 22, 52, 43)"""
    if s.startswith('['):
        words = ARRAY_SPLIT_RE.split(s)
    else:
        words = [s]
    for word in words:
        safe = False
        string_delimiter = None
        word = word.strip()
        if not word:
            safe = True
        else:
            for d in ["'", '"']:
                if word.startswith(d):
                    string_delimiter = d
                    break
            if string_delimiter:
                safe = True
                if not word.endswith(string_delimiter):
                    safe = False
                fragments = word[1:-1].split(string_delimiter)[0:-1]
                if fragments:
                    for fragment in fragments:
                        m = COUNT_SLASHES_RE.search(fragment)
                        if m.groups() and len(m.groups()[0]) % 2 == 0:
                            safe = False
                            break
            else:
                try:
                    int(s)
                    safe = True
                except ValueError:
                    pass
                if DATETIME_RE.fullmatch(s):
                    safe = True
        if not safe:
            return False
    return True


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
        v_str = line[space_index + 1:].strip()
        if not _is_eval_safe(v_str):
            warn(f'invalid line in stdout of moin index-dump: {repr(line.strip())}')
            continue
        item[line[0:space_index]] = eval(v_str)
