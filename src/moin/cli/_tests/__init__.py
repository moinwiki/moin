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
import sys
from typing import Union
from warnings import warn

from moin._tests import get_dirs
from moin import log

logging = log.getLogger(__name__)


def run(
    cmd: list[str], log=None, wait: bool = True, timeout: int = None, env=None
) -> Union[subprocess.CompletedProcess, subprocess.Popen]:
    """run a shell command, redirecting output to log
    :param cmd: list of strings containing command arguments
    :param log: open file handle to log file (binary mode) or None in which case output will be captured
    :param wait: if True return after process is complete, otherwise return immediately after start
    :param timeout: timeout setting in seconds, can only be used when wait is True
    :param env: dictionary of environment variables to add to current env for subprocess
    :return: CompletedProcess object if wait else Popen object"""
    subprocess_environ = copy(os.environ)
    subprocess_environ["PYTHONIOENCODING"] = "cp1252"  # simulate windows terminal to ferret out encoding issues
    if env:
        subprocess_environ.update(env)
    logging.info(f"running {cmd}")
    if stdout := log:
        stderr = subprocess.STDOUT
    else:  # log is None
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    kwargs = {}
    flags = 0
    if wait:
        run_func = subprocess.run
        kwargs["timeout"] = timeout
    else:
        run_func = subprocess.Popen
        if sys.platform == "win32":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP  # needed for use of os.kill
    return run_func(cmd, stdout=stdout, stderr=stderr, creationflags=flags, env=subprocess_environ, **kwargs)


def assert_p_succcess(p: subprocess.CompletedProcess):
    """assert returncode 0 and print logs on error"""
    try:
        assert p.returncode == 0
    except AssertionError:
        logging.error(f"failure for {p.args} stdout = {p.stdout} stderr = {p.stderr}")
        raise


ARRAY_SPLIT_RE = re.compile(r"[\[\],]")
DATETIME_RE = re.compile(r"datetime\.datetime\([\d, ]*\)")
COUNT_SLASHES_RE = re.compile(r"([\\]*)$")


def _is_eval_safe(s: str) -> bool:
    """validate that s is one of the expected formats in output of moin index-dump

    valid strings include
    'a string'
    'a string doesn\'t have to be simple'
    ['one', 'two']
    []
    123
    datetime.datetime(2023, 4, 17, 22, 52, 43)"""
    if s.startswith("["):
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
                if s in {"True", "False"}:
                    safe = True
        if not safe:
            return False
    return True


def read_index_dump(out: str, latest=False):
    """parse output of moin dump-index yielding the items

    :param out: stdout of `moin index-dump --no-truncate` command
    :param latest: if True yield only the latest revs
    :return: list of dicts with key value pairs from output"""
    if not isinstance(out, str):
        raise ValueError("read_index_dump_latest_revs expects str, did you forget to .decode()")
    item = {}
    for line in out.splitlines():
        if not line.strip() or line.startswith(" "):
            if item:
                yield item
                item = {}
            if latest and "all_revs" in line:
                break
            continue
        space_index = line.index(" ")
        v_str = line[space_index + 1 :].strip()
        if not _is_eval_safe(v_str):
            warn(f"invalid line in stdout of moin index-dump: {repr(line.strip())}")
            continue
        item[line[0:space_index]] = eval(v_str)


def read_index_dump_latest_revs(out: str):
    """parse output of moin dump-index yielding the items in latest revs see :py:func:`read_index_dump`"""
    yield from read_index_dump(out, True)


def getBackupPath(backup_name):
    _, artifact_base_dir = get_dirs("")
    return artifact_base_dir / backup_name
