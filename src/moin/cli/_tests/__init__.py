# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - common helper functions for moin.cli tests.
"""

from __future__ import annotations

import datetime  # noqa
import os
import re
import subprocess
import sys

from copy import copy
from typing import Any, IO, Sequence
from warnings import warn

from moin._tests import get_dirs
from moin import log
from moin.constants.keys import ALL_REVS, LATEST_META

logging = log.getLogger(__name__)


def run(
    cmd: Sequence[str | os.PathLike],
    log: int | IO[Any] | None = None,
    wait: bool = True,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess | subprocess.Popen:
    """Run a shell command, redirecting output to a log.

    :param cmd: List of strings containing command arguments.
    :param log: Open file handle to a log file (binary mode) or None, in which case output will be captured.
    :param wait: If True, return after the process completes; otherwise, return immediately after start.
    :param timeout: Timeout in seconds; can only be used when wait is True.
    :param env: Dictionary of environment variables to add to the current environment for the subprocess.
    :return: CompletedProcess object if wait is True; otherwise, a Popen object."""
    subprocess_environ = copy(os.environ)
    subprocess_environ["PYTHONIOENCODING"] = "cp1252"  # Simulate Windows terminal to ferret out encoding issues
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
    """Assert returncode 0 and print logs on error."""
    try:
        assert p.returncode == 0
    except AssertionError:
        logging.error(f"failure for {p.args} stdout = {p.stdout} stderr = {p.stderr}")
        raise


ARRAY_SPLIT_RE = re.compile(r"[\[\],]")
DATETIME_RE = re.compile(r"datetime\.datetime\([\d, ]*\)")
COUNT_SLASHES_RE = re.compile(r"([\\]*)$")


def _is_eval_safe(s: str) -> bool:
    """Validate that s matches one of the expected formats in the output of 'moin index-dump'.

    Valid strings include
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
    """Parse the output of 'moin index-dump', yielding the items.

    :param out: stdout of the `moin index-dump --no-truncate` command.
    :param latest: If True, yield only the latest revisions.
    :return: List of dicts with key/value pairs from the output."""
    if not isinstance(out, str):
        raise ValueError("read_index_dump_latest_revs expects str, did you forget to .decode()")
    item = {}
    for line in out.splitlines():
        if not line.strip() or line.startswith(" "):
            if item:
                yield item
                item = {}
            if latest and ALL_REVS in line:
                break
            if LATEST_META in line:
                break
            continue
        space_index = line.index(" ")
        v_str = line[space_index + 1 :].strip()
        if not _is_eval_safe(v_str):
            warn(f"invalid line in stdout of moin index-dump: {repr(line.strip())}")
            continue
        item[line[0:space_index]] = eval(v_str)


def read_index_dump_latest_revs(out: str):
    """Parse the output of 'moin index-dump' yielding only the latest revisions; see :py:func:`read_index_dump`."""
    yield from read_index_dump(out, True)


def getBackupPath(backup_name):
    _, artifact_base_dir = get_dirs("")
    return artifact_base_dir / backup_name
